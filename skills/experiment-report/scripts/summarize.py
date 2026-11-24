#!/usr/bin/env python3
"""
summarize.py - descriptive statistics for experiment results (CSV / TSV / XLSX).

Usage
  python summarize.py results.csv                          # profile only: columns, types, missing values
  python summarize.py results.csv --group method --metrics accuracy,f1
  python summarize.py results.csv --group method --compare baseline --out report/A --filter dataset=A
  python summarize.py results.csv --group method --compare baseline --pair "ours+aug:ours"
  python summarize.py results.csv --group method --exclude-rows 15     # e.g. a crashed run
  python summarize.py log.csv --group method --metrics val_loss --filter epoch=20   # end of a learning curve

Outputs (in --out, default ./experiment_report)
  summary.json   every number (the single source of truth for the written report)
  summary.md     the same numbers as readable tables (one rounding per metric)

--compare REF runs Welch's t-test of every group against REF; --pair A:B adds more
comparisons. All comparisons of one metric form one Holm family.
Standard library only (openpyxl is needed for .xlsx).
"""

import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tableio as T  # noqa: E402


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Summarize experiment results.")
    ap.add_argument("input")
    ap.add_argument("--sheet", help="xlsx sheet name (default: first sheet)")
    ap.add_argument("--group", default="", help="comma-separated condition columns, e.g. method,dataset")
    ap.add_argument("--metrics", default="", help="comma-separated metric columns (default: all numeric, minus id-like columns)")
    ap.add_argument("--compare", help="reference group label for Welch t-tests, e.g. baseline")
    ap.add_argument("--pair", action="append", default=[], help="extra comparison 'A:B' (A minus B); repeatable")
    ap.add_argument("--order", default="", help="comma-separated group order for tables")
    ap.add_argument("--filter", action="append", default=[], help="keep rows where col=value (or col!=value); repeatable")
    ap.add_argument("--exclude-rows", default="", help="spreadsheet row numbers to drop, e.g. 15,22 (header is row 1)")
    ap.add_argument("--out", default="experiment_report", help="output folder; use one folder per analysis")
    args = ap.parse_args()

    header, rows, info = T.read_table(args.input, args.sheet)
    rows = T.apply_filters(rows, args.filter)
    rows, dropped = T.exclude_rows(rows, args.exclude_rows)
    prof = T.profile_columns(header, rows)
    numeric = [p["name"] for p in prof if p["type"] == "numeric"]
    group_cols = [g.strip() for g in args.group.split(",") if g.strip()]
    for g in group_cols:
        if g not in header:
            raise SystemExit(f"Group column '{g}' not found. Columns: {', '.join(header)}")
    profile_only = not group_cols and not args.metrics

    excluded = []
    metrics = []
    if args.metrics:
        metrics = [m.strip() for m in args.metrics.split(",") if m.strip()]
        for m in metrics:
            if m not in header:
                raise SystemExit(f"Metric column '{m}' not found. Columns: {', '.join(header)}")
    elif not profile_only:
        for c in numeric:
            if c in group_cols:
                continue
            if T.ID_LIKE.match(c):
                excluded.append(c)
                continue
            metrics.append(c)

    order = [o.strip() for o in args.order.split(",") if o.strip()]
    groups = T.ordered_groups(rows, group_cols, order)
    notes = []
    if dropped:
        notes.append(f"rows excluded on request: {', '.join(map(str, dropped))}")

    stats, values_by, decimals = {}, {}, {}
    for m in metrics:
        stats[m], values_by[m] = {}, {}
        decimals[m] = T.decimals_for([T.parse_number(r[m]) for r in rows])
        for g in groups:
            sub = [r for r in rows if T.group_label(r, group_cols) == g]
            pairs = [(r["_row"], T.parse_number(r[m])) for r in sub]
            vals = [v for _, v in pairs if v is not None]
            d = T.describe(vals)
            d["missing"] = sum(1 for _, v in pairs if v is None)
            d["missing_rows"] = [r for r, v in pairs if v is None]
            d["outliers"] = T.robust_outliers([(r, v) for r, v in pairs if v is not None])
            stats[m][g] = d
            values_by[m][g] = vals
            if d["missing"]:
                notes.append(f"{m} / {g}: {d['missing']} missing or non-numeric value(s) excluded "
                             f"(row {', '.join(map(str, d['missing_rows']))})")
            if 0 < d["n"] < 3:
                notes.append(f"{m} / {g}: n={d['n']}, too small for a reliable CI or test")
            if d["outliers"]:
                rows_txt = ", ".join(f"row {o['row']} ({T.fmt_d(o['value'], decimals[m])})" for o in d["outliers"])
                notes.append(f"{m} / {g}: possible outlier (Grubbs test, alpha=0.01) at {rows_txt}; "
                             f"to see results without it, re-run with --exclude-rows")

    # ---- comparisons: one Holm family per metric
    plan = []
    if args.compare:
        if args.compare not in groups:
            raise SystemExit(f"--compare '{args.compare}' is not a group. Groups: {', '.join(groups)}")
        plan += [(g, args.compare) for g in groups if g != args.compare]
    for p in args.pair:
        if ":" not in p:
            raise SystemExit(f"--pair must look like A:B, got '{p}'")
        a, b = (x.strip() for x in p.split(":", 1))
        for x in (a, b):
            if x not in groups:
                raise SystemExit(f"--pair group '{x}' not found. Groups: {', '.join(groups)}")
        if (a, b) not in plan:
            plan.append((a, b))
    comparisons = {}
    if plan:
        for m in metrics:
            comps = []
            for a, b in plan:
                w = T.welch(values_by[m][a], values_by[m][b])
                rec = {"group": a, "reference": b, "n_group": len(values_by[m][a]), "n_reference": len(values_by[m][b])}
                if w is None:
                    rec.update({"t": None, "p": None, "note": "fewer than 2 values in a group; no test"})
                else:
                    rec.update(w)
                    if rec.get("cohen_d") is not None and abs(rec["cohen_d"]) > 5:
                        notes.append(f"{m}: {a} vs {b} has a very large Cohen's d ({rec['cohen_d']:.1f}); "
                                     f"this happens when the SD is tiny, so lead with the raw difference")
                comps.append(rec)
            adj = T.holm([c.get("p") for c in comps])
            for c, a_ in zip(comps, adj):
                c["p_holm"] = a_
            comparisons[m] = comps
        if len(plan) > 1:
            notes.append(f"{len(plan)} comparisons per metric; use p_holm (Holm-corrected within each metric). "
                         f"Tests in separate runs (e.g. per dataset) are not corrected together")

    os.makedirs(args.out, exist_ok=True)
    out = {"tool": "experiment-report/summarize.py 0.2.0", "input": info, "filters": args.filter,
           "excluded_rows": dropped, "group_by": group_cols, "groups": groups, "metrics": metrics,
           "decimals": decimals, "excluded_numeric_columns": excluded, "columns": prof,
           "stats": stats, "comparisons": comparisons, "notes": notes}
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    # ---- markdown
    L = [f"# Summary: {info['file']}", ""]
    scope = []
    if args.filter:
        scope.append(f"filters: {', '.join(args.filter)}")
    if dropped:
        scope.append(f"excluded rows: {', '.join(map(str, dropped))}")
    L.append(f"- Rows: {len(rows)}" + (f" ({'; '.join(scope)})" if scope else ""))
    if group_cols:
        L.append(f"- Grouped by: {', '.join(group_cols)} ({len(groups)} groups)")
    if excluded:
        L.append(f"- Numeric columns treated as IDs and not summarized: {', '.join(excluded)} (pass --metrics to include)")
    if profile_only:
        L.append("- Profile only. Re-run with --group (and --compare) to compute statistics.")
    L += ["", "## Columns", "", "| Column | Type | Non-missing | Missing | Unique | Examples |", "|---|---|---|---|---|---|"]
    for p in prof:
        L.append(f"| {p['name']} | {p['type']} | {p['non_missing']} | {p['missing']} | {p['unique']} | "
                 f"{', '.join(p['examples'])} |")
    for m in metrics:
        k = decimals[m]
        f = lambda x: T.fmt_d(x, k)  # noqa: E731
        L += ["", f"## {m}", "", "| Group | n | Mean ± SD | 95% CI | Median [Q1, Q3] | Min – Max |",
              "|---|---|---|---|---|---|"]
        for g in groups:
            d = stats[m][g]
            if d["n"] == 0:
                L.append(f"| {g} | 0 | - | - | - | - |")
                continue
            ci = f"[{f(d['ci95'][0])}, {f(d['ci95'][1])}]" if "ci95" in d else "-"
            iq = f"{f(d['median'])} [{f(d['q1'])}, {f(d['q3'])}]" if "q1" in d else f(d["median"])
            L.append(f"| {g} | {d['n']} | {f(d['mean'])} ± {f(d.get('sd'))} | {ci} | {iq} | "
                     f"{f(d['min'])} – {f(d['max'])} |")
        if m in comparisons:
            L += ["", "Welch's t-test (difference = group − reference)", "",
                  "| Group | Reference | Mean diff | 95% CI of diff | t | df | p | p (Holm) | Cohen's d |",
                  "|---|---|---|---|---|---|---|---|---|"]
            for c in comparisons[m]:
                if c.get("t") is None:
                    L.append(f"| {c['group']} | {c['reference']} | {f(c.get('mean_diff'))} | - | - | - | - | - | - |")
                    continue
                L.append(f"| {c['group']} | {c['reference']} | {f(c['mean_diff'])} | [{f(c['ci95_diff'][0])}, "
                         f"{f(c['ci95_diff'][1])}] | {c['t']:.2f} | {c['df']:.1f} | "
                         f"{T.fmt_p(c['p'])} | {T.fmt_p(c['p_holm'])} | "
                         f"{'-' if c['cohen_d'] is None else format(c['cohen_d'], '.2f')} |")
    if notes:
        L += ["", "## Notes", ""] + [f"- {n}" for n in notes]
    with open(os.path.join(args.out, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")

    if profile_only:
        print(f"{len(rows)} rows, {len(header)} columns (profile only). Numeric: {', '.join(numeric) or '-'}")
    else:
        print(f"{len(rows)} rows, {len(groups)} group(s), {len(metrics)} metric(s): {', '.join(metrics)}")
    if excluded:
        print(f"Excluded id-like numeric columns: {', '.join(excluded)}")
    for n in notes:
        print(f"NOTE: {n}")
    print(f"Wrote {os.path.join(args.out, 'summary.json')} and summary.md")


if __name__ == "__main__":
    main()

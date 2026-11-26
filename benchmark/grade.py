#!/usr/bin/env python3
"""
grade.py - score the runs.

  python grade.py citation      # automatic: verdicts.csv vs tasks/citation/answer_key.json
  python grade.py blind         # experiment: copy each run's report + figures to grading/ under
                                #   anonymous IDs (the grader never sees which condition it is)
  python grade.py aggregate     # merge scores + meta.json into results/results.md and results.json

Set BENCH_HOME the same way as for run_benchmark.py: runs/ and grading/ live there,
results/ stays next to this file.

The experiment task is graded by a separate reviewer (person or a fresh AI agent with no
knowledge of the conditions) using tasks/experiment/rubric.md. The reviewer writes
grading/grades.json: {"<anon id>": {"items": {"1": 1, "2": 0, ...}, "notes": "..."}}.
"""

import csv
import glob
import io
import json
import os
import random
import shutil
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.abspath(os.environ.get("BENCH_HOME") or HERE)   # same as run_benchmark.py
RUNS = os.path.join(HOME, "runs")
GRADING = os.path.join(HOME, "grading")
LABELS_EXIST = {"OK", "WRONG_METADATA", "WRONG_ID", "FAKE", "UNSURE"}


def read_verdicts(run_dir):
    paths = glob.glob(os.path.join(run_dir, "**", "verdicts.csv"), recursive=True)
    if not paths:
        return None
    raw = open(paths[0], "rb").read()
    for enc in ("utf-8-sig", "cp949", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    rows = list(csv.DictReader(io.StringIO(text)))
    out = {}
    for r in rows:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        ref = r.get("ref", "").strip("[]# ")
        if ref:
            out[ref] = {"existence": r.get("existence", "").upper(), "claim": r.get("claim", "").upper()}
    return out


def grade_citation():
    key = json.load(open(os.path.join(HERE, "tasks", "citation", "answer_key.json"), encoding="utf-8"))
    for run_dir in sorted(glob.glob(os.path.join(RUNS, "citation", "*", "run-*"))):
        v = read_verdicts(run_dir)
        res = {"has_output": v is not None, "existence": {}, "claim": {}}
        if v:
            for ref, k in key["existence"].items():
                got = (v.get(ref) or {}).get("existence", "")
                ok = [k["truth"]] + k.get("also", [])
                res["existence"][ref] = {"got": got, "truth": k["truth"],
                                         "score": 1.0 if got in ok else 0.5 if got in k["half"] else 0.0}
            for ref, k in key["claim"].items():
                got = (v.get(ref) or {}).get("claim", "")
                res["claim"][ref] = {"got": got, "accept": k["accept"],
                                     "score": 1.0 if got in k["accept"] else 0.5 if got in k["half"] else 0.0}
        ex = [x["score"] for x in res["existence"].values()]
        cl = [x["score"] for x in res["claim"].values()]
        real = [r for r, k in key["existence"].items() if k["truth"] in ("OK", "WRONG_METADATA")]
        fake = [r for r, k in key["existence"].items() if k["truth"] == "FAKE"]
        res["existence_score"] = round(sum(ex) / len(key["existence"]), 3)
        res["claim_score"] = round(sum(cl) / len(key["claim"]), 3)
        res["false_accusations"] = sum(1 for r in real if res["existence"].get(r, {}).get("got") == "FAKE")
        res["missed_fakes"] = sum(1 for r in fake if res["existence"].get(r, {}).get("got") == "OK")
        res["score"] = round((sum(ex) + sum(cl)) / (len(key["existence"]) + len(key["claim"])), 3)
        with open(os.path.join(run_dir, "grade.json"), "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=2)
        print(f"{os.path.relpath(run_dir, RUNS)}: score {res['score']} (existence {res['existence_score']}, "
              f"claim {res['claim_score']}, false accusations {res['false_accusations']}, missed fakes {res['missed_fakes']})")


def blind():
    gdir = GRADING
    if os.path.exists(gdir):
        shutil.rmtree(gdir)
    runs = sorted(glob.glob(os.path.join(RUNS, "experiment", "*", "run-*")))
    ids = [f"R{n:02d}" for n in range(1, len(runs) + 1)]
    random.Random(7).shuffle(ids)
    mapping = {}
    for anon, run_dir in zip(ids, runs):
        dst = os.path.join(gdir, anon)
        os.makedirs(dst)
        reports = glob.glob(os.path.join(run_dir, "**", "report.md"), recursive=True)
        if reports:
            shutil.copy(reports[0], os.path.join(dst, "report.md"))
        for png in glob.glob(os.path.join(run_dir, "**", "*.png"), recursive=True):
            name = os.path.relpath(png, run_dir).replace(os.sep, "__")
            shutil.copy(png, os.path.join(dst, name))
        mapping[anon] = os.path.relpath(run_dir, HOME)
    with open(os.path.join(RUNS, "blind_mapping.json"), "w", encoding="utf-8") as fh:
        json.dump(mapping, fh, indent=2)
    print(f"{len(runs)} runs copied to {gdir} as {', '.join(sorted(ids))}. Mapping kept in runs/blind_mapping.json.")


def msd(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None, None
    return statistics.fmean(xs), (statistics.stdev(xs) if len(xs) > 1 else 0.0)


def aggregate():
    rows = []
    grades = {}
    gpath = os.path.join(GRADING, "grades.json")
    mpath = os.path.join(RUNS, "blind_mapping.json")
    if os.path.exists(gpath) and os.path.exists(mpath):
        g = json.load(open(gpath, encoding="utf-8"))
        m = json.load(open(mpath, encoding="utf-8"))
        for anon, rel in m.items():
            if anon in g:
                items = g[anon]["items"]
                grades[os.path.normpath(os.path.join(HOME, rel))] = {
                    "score": round(sum(items.values()) / len(items), 3), "items": items, "notes": g[anon].get("notes")}
    for meta_path in sorted(glob.glob(os.path.join(RUNS, "*", "*", "run-*", "meta.json"))):
        run_dir = os.path.dirname(meta_path)
        meta = json.load(open(meta_path, encoding="utf-8"))
        row = {k: meta.get(k) for k in ("task", "condition", "run", "status", "duration_s", "wall_s", "num_turns",
                                         "tool_calls", "output_tokens", "cost_usd_equivalent",
                                         "skill_invoked", "skill_script_used")}
        gp = os.path.join(run_dir, "grade.json")
        if os.path.exists(gp):
            gr = json.load(open(gp, encoding="utf-8"))
            row.update({"score": gr["score"], "existence_score": gr["existence_score"], "claim_score": gr["claim_score"],
                        "false_accusations": gr["false_accusations"], "missed_fakes": gr["missed_fakes"]})
        elif os.path.normpath(run_dir) in grades:
            row.update({"score": grades[os.path.normpath(run_dir)]["score"],
                        "rubric_items": grades[os.path.normpath(run_dir)]["items"]})
        rows.append(row)

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "results.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)
    flat = os.path.join(HERE, "results", "runs.csv")
    cols = ["task", "condition", "run", "status", "score", "existence_score", "claim_score", "false_accusations",
            "missed_fakes", "duration_s", "num_turns", "tool_calls", "output_tokens", "cost_usd_equivalent",
            "skill_invoked", "skill_script_used"]
    with open(flat, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    L = ["# Results: with skill vs without skill", "",
         "| Task | Condition | n | Score (mean ± SD) | Time, s (mean ± SD) | Turns | Output tokens | Skill used |",
         "|---|---|---|---|---|---|---|---|"]
    for task in ("citation", "experiment"):
        for cond in ("baseline", "skill"):
            rs = [r for r in rows if r["task"] == task and r["condition"] == cond]
            if not rs:
                continue
            sm, ss = msd([r.get("score") for r in rs])
            tm, ts = msd([r.get("duration_s") for r in rs])
            nm, _ = msd([r.get("num_turns") for r in rs])
            om, _ = msd([r.get("output_tokens") for r in rs])
            used = sum(1 for r in rs if r.get("skill_invoked") or r.get("skill_script_used"))
            f = lambda m, s, d=2: "-" if m is None else f"{m:.{d}f} ± {s:.{d}f}"  # noqa: E731
            L.append(f"| {task} | {cond} | {len(rs)} | {f(sm, ss)} | {f(tm, ts, 0)} | "
                     f"{'-' if nm is None else f'{nm:.0f}'} | {'-' if om is None else f'{om:,.0f}'} | {used}/{len(rs)} |")
    cit = [r for r in rows if r["task"] == "citation" and "false_accusations" in r]
    if cit:
        L += ["", "Citation task details", "", "| Condition | Existence score | Claim score | False accusations (real→FAKE) | Missed fakes (FAKE→OK) |",
              "|---|---|---|---|---|"]
        for cond in ("baseline", "skill"):
            rs = [r for r in cit if r["condition"] == cond]
            if rs:
                em, es = msd([r["existence_score"] for r in rs])
                cm, cs = msd([r["claim_score"] for r in rs])
                L.append(f"| {cond} | {em:.2f} ± {es:.2f} | {cm:.2f} ± {cs:.2f} | "
                         f"{sum(r['false_accusations'] for r in rs)} | {sum(r['missed_fakes'] for r in rs)} |")
    with open(os.path.join(HERE, "results", "results.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))

    # figures, drawn with the experiment-report skill's own plot.py. With n = 3 per group a 95% CI
    # is very wide (and runs past the 0-1 score range), so show every run plus the mean instead.
    import subprocess
    plot = os.path.join(os.path.dirname(HERE), "skills", "experiment-report", "scripts", "plot.py")
    if any(r.get("score") is not None for r in rows):
        subprocess.run([sys.executable, plot, flat, "--kind", "point", "--x", "task", "--y", "score,duration_s",
                        "--hue", "condition", "--hue-order", "baseline,skill", "--order", "citation,experiment",
                        "--error", "none", "--rotate", "0", "--xlabel", "Task",
                        "--ylabel", "Score (0-1),Time (s)", "--out", os.path.join(HERE, "results", "comparison.png")])


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"citation": grade_citation, "blind": blind, "aggregate": aggregate}.get(cmd, lambda: print(__doc__))()

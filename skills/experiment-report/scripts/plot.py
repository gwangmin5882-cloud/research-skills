#!/usr/bin/env python3
"""
plot.py - publication-style figures for experiment results (needs matplotlib).

Kinds
  bar      mean per group with error bars and the individual points   (final results)
  point    mean ± error without bars; use when differences are small   (final results)
  box      distribution per group with the individual points
  line     metric over a numeric x (epoch, step, size), one line per --hue, mean ± band
  scatter  two numeric columns, coloured by --hue

Usage
  python plot.py results.csv --kind bar   --x method --y accuracy --out figs/accuracy.png
  python plot.py results.csv --kind point --x method --y accuracy,f1 --hue dataset
  python plot.py log.csv     --kind line  --x epoch  --y val_loss --hue method --error sd
  python plot.py results.csv --kind box   --x method --y latency_ms --order baseline,ours

Every run prints what the error bars mean and the n per group, and writes the same
facts to <out>.json so captions can quote them exactly.
"""

import argparse
import json
import math
import os
import random
import re
import statistics
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tableio as T  # noqa: E402

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager, rcParams
    from matplotlib.ticker import MaxNLocator
except ImportError:
    raise SystemExit("plot.py needs matplotlib: pip install matplotlib")

PALETTE = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]  # Okabe-Ito
HANGUL = re.compile(r"[ㄱ-ㆎ가-힣]")
CJK_FONTS = ["Malgun Gothic", "AppleGothic", "Apple SD Gothic Neo", "NanumGothic", "NanumBarunGothic",
             "Noto Sans CJK KR", "Noto Sans KR", "Source Han Sans KR", "UnDotum", "Gulim"]


def setup_font(texts):
    rcParams["axes.unicode_minus"] = False
    need = any(HANGUL.search(t or "") for t in texts)
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in CJK_FONTS:
        if name in available:
            rcParams["font.family"] = [name, "DejaVu Sans"]
            return name, need
    if need:
        print("WARNING: labels contain Hangul but no Korean font was found; text may render as boxes. "
              "Install e.g. Noto Sans KR / NanumGothic, or use English labels.", file=sys.stderr)
    return None, need


def err_value(vals, mode):
    n = len(vals)
    if n < 2 or mode == "none":
        return 0.0
    sd = statistics.stdev(vals)
    if mode == "sd":
        return sd
    sem = sd / math.sqrt(n)
    if mode == "sem":
        return sem
    return T.t_crit(n - 1) * sem   # ci95


ERR_LABEL = {"ci95": "95% CI", "sd": "±1 SD", "sem": "±1 SEM", "none": "none"}


def numeric_values(rows, col):
    return [T.parse_number(r[col]) for r in rows]


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Plot experiment results.")
    ap.add_argument("input")
    ap.add_argument("--sheet")
    ap.add_argument("--kind", choices=["bar", "point", "box", "line", "scatter"], default="bar")
    ap.add_argument("--x", required=True, help="group column (bar/point/box) or numeric column (line/scatter)")
    ap.add_argument("--y", required=True, help="metric column(s), comma-separated -> one panel each")
    ap.add_argument("--hue", help="second grouping column (colour)")
    ap.add_argument("--error", choices=["ci95", "sd", "sem", "none"], default="ci95")
    ap.add_argument("--order", default="", help="comma-separated order of x groups")
    ap.add_argument("--hue-order", default="")
    ap.add_argument("--filter", action="append", default=[], help="col=value or col!=value; repeatable")
    ap.add_argument("--exclude-rows", default="", help="spreadsheet row numbers to drop, e.g. 15,22")
    ap.add_argument("--title", default="")
    ap.add_argument("--xlabel")
    ap.add_argument("--ylabel", help="y label(s) with units; comma-separated, one per metric in --y")
    ap.add_argument("--rotate", type=float, help="x tick label rotation in degrees (default: auto)")
    ap.add_argument("--legend", choices=["auto", "inside", "outside", "none"], default="auto")
    ap.add_argument("--no-points", action="store_true", help="hide individual data points")
    ap.add_argument("--ylim", help="lo,hi")
    ap.add_argument("--logy", action="store_true")
    ap.add_argument("--width", type=float)
    ap.add_argument("--height", type=float, default=4.2)
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--out", default="figure.png")
    args = ap.parse_args()

    header, rows, info = T.read_table(args.input, args.sheet)
    rows = T.apply_filters(rows, args.filter)
    rows, dropped = T.exclude_rows(rows, args.exclude_rows)
    metrics = [m.strip() for m in args.y.split(",") if m.strip()]
    ylabels = [y.strip() for y in args.ylabel.split(",")] if args.ylabel else []
    if ylabels and len(ylabels) != len(metrics):
        raise SystemExit(f"--ylabel has {len(ylabels)} label(s) but --y has {len(metrics)} metric(s)")
    for c in [args.x] + metrics + ([args.hue] if args.hue else []):
        if c not in header:
            raise SystemExit(f"Column '{c}' not found. Columns: {', '.join(header)}")

    order = [o.strip() for o in args.order.split(",") if o.strip()]
    hue_order = [o.strip() for o in args.hue_order.split(",") if o.strip()]
    categorical = args.kind in ("bar", "point", "box")
    xs = T.ordered_groups(rows, [args.x], order) if categorical else []
    hues = T.ordered_groups(rows, [args.hue], hue_order) if args.hue else [None]

    font, _ = setup_font(xs + [h or "" for h in hues] + metrics + [args.title, args.xlabel or "", args.ylabel or "", args.x])

    n_panels = len(metrics)
    n_cats = max(1, len(xs))
    width = args.width or min(14.0, max(5.0, 3.0 + 0.55 * n_cats * max(1, len(hues)) ** 0.6)) * (1 if n_panels == 1 else 0.8)
    fig, axes = plt.subplots(1, n_panels, figsize=(width * n_panels, args.height), squeeze=False)
    axes = axes[0]
    rng = random.Random(0)
    meta = {"file": os.path.basename(args.out), "kind": args.kind, "x": args.x, "y": metrics, "hue": args.hue,
            "error_bars": ERR_LABEL[args.error] if args.kind in ("bar", "point", "line") else None,
            "filters": args.filter, "font": font, "n": {}}

    hints = []
    for ax, metric in zip(axes, metrics):
        meta["n"][metric] = {}
        bar_means = []
        if categorical:
            k = len(hues)
            span = 0.8
            w = span / k
            for hi, h in enumerate(hues):
                color = PALETTE[hi % len(PALETTE)]
                means, errs, pos = [], [], []
                for xi, xv in enumerate(xs):
                    sub = [r for r in rows if r[args.x] == xv and (h is None or r[args.hue] == h)]
                    vals = [v for v in numeric_values(sub, metric) if v is not None]
                    key = xv if h is None else f"{xv} / {h}"
                    meta["n"][metric][key] = len(vals)
                    p = xi - span / 2 + w * (hi + 0.5)
                    if not vals:
                        continue
                    pos.append(p)
                    means.append(statistics.fmean(vals))
                    errs.append(err_value(vals, args.error))
                    if args.kind == "box":
                        ax.boxplot([vals], positions=[p], widths=w * 0.7, patch_artist=True, showfliers=False,
                                   boxprops=dict(facecolor=color + "55", edgecolor=color),
                                   medianprops=dict(color=color), whiskerprops=dict(color=color),
                                   capprops=dict(color=color))
                    if not args.no_points and len(vals) <= 80:
                        jit = [p + (rng.random() - 0.5) * w * 0.45 for _ in vals]
                        ax.scatter(jit, vals, s=14, color="#222222" if args.kind == "bar" else color,
                                   alpha=0.55, zorder=3, linewidths=0)
                label = h if h is not None else None
                if args.kind == "bar":
                    bar_means.extend(means)
                    ax.bar(pos, means, width=w * 0.9, color=color, alpha=0.85, label=label,
                           yerr=errs if args.error != "none" else None, capsize=4,
                           error_kw=dict(elinewidth=1.2, ecolor="#333333"), zorder=2)
                elif args.kind == "point":
                    ax.errorbar(pos, means, yerr=errs if args.error != "none" else None, fmt="o", color=color,
                                ms=7, capsize=4, elinewidth=1.5, label=label, zorder=4)
                elif args.kind == "box" and label:
                    ax.plot([], [], color=color, lw=6, alpha=0.5, label=label)
            ax.set_xticks(range(len(xs)))
            ax.set_xticklabels(xs)
            rot = args.rotate
            if rot is None:
                longest = max((len(x) for x in xs), default=0)
                rot = 30 if (longest > 9 or len(xs) > 6) else 0
            if rot:
                plt.setp(ax.get_xticklabels(), rotation=rot, ha="right", rotation_mode="anchor")
            ax.set_xlim(-0.6, len(xs) - 0.4)
        else:
            for hi, h in enumerate(hues):
                color = PALETTE[hi % len(PALETTE)]
                sub = [r for r in rows if h is None or r[args.hue] == h]
                pts = [(T.parse_number(r[args.x]), T.parse_number(r[metric])) for r in sub]
                pts = [(a, b) for a, b in pts if a is not None and b is not None]
                if not pts:
                    meta["n"][metric][h or "all"] = 0
                    continue
                if args.kind == "scatter":
                    meta["n"][metric][h or "all"] = len(pts)
                    ax.scatter([a for a, _ in pts], [b for _, b in pts], s=18, color=color, alpha=0.75, label=h)
                    continue
                by_x = {}
                for a, b in pts:
                    by_x.setdefault(a, []).append(b)
                xv = sorted(by_x)
                meta["n"][metric][h or "all"] = min(len(by_x[a]) for a in xv)   # runs per x point
                mv = [statistics.fmean(by_x[a]) for a in xv]
                ev = [err_value(by_x[a], args.error) for a in xv]
                if all(float(a).is_integer() for a in xv):
                    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
                ax.plot(xv, mv, color=color, lw=1.8, label=h, marker="o" if len(xv) <= 15 else None, ms=4)
                if any(e > 0 for e in ev):
                    ax.fill_between(xv, [m - e for m, e in zip(mv, ev)], [m + e for m, e in zip(mv, ev)],
                                    color=color, alpha=0.18, linewidth=0)
        if bar_means and min(bar_means) > 0 and (max(bar_means) - min(bar_means)) / max(bar_means) < 0.1:
            hints.append(f"{metric}: group means differ by <10% of the bar height, so bars starting at 0 "
                         f"hide the differences. Consider --kind point (y axis not forced to 0).")
        ax.set_ylabel(ylabels[metrics.index(metric)] if ylabels else metric)
        ax.set_xlabel(args.xlabel if args.xlabel is not None else args.x)
        if args.logy:
            ax.set_yscale("log")
        if args.ylim:
            lo, hi_ = (float(v) for v in args.ylim.split(","))
            ax.set_ylim(lo, hi_)
        ax.grid(axis="y", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)

    # legend
    handles, labels = axes[0].get_legend_handles_labels()
    if handles and args.legend != "none":
        title = args.hue
        # categorical panels are crowded (bars, error bars, points), so their legend goes outside by default
        outside = args.legend == "outside" or (args.legend == "auto" and (categorical or len(labels) > 4))
        if outside:
            axes[-1].legend(handles, labels, title=title, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0))
        else:
            axes[0].legend(handles, labels, title=title, frameon=False)

    # caption line: what the error bars mean and n
    n_all = [v for d in meta["n"].values() for v in d.values()]
    n_txt = f"n = {min(n_all)}" if n_all and min(n_all) == max(n_all) else (f"n = {min(n_all)}–{max(n_all)}" if n_all else "")
    cap = []
    if meta["error_bars"] and args.error != "none":
        cap.append(("band" if args.kind == "line" else "error bars") + f": {ERR_LABEL[args.error]}")
    if n_txt:
        cap.append(n_txt + (" per point" if args.kind == "line" else " per group"))
    if cap:
        fig.text(0.995, 0.005, "; ".join(cap), ha="right", va="bottom", fontsize=8, color="#666666")
    if args.title:
        fig.suptitle(args.title)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    fig.savefig(args.out, dpi=args.dpi, bbox_inches="tight")
    plt.close(fig)
    meta["caption_hint"] = "; ".join(cap)
    meta["hints"] = hints
    for h in hints:
        print(f"HINT: {h}")
    with open(os.path.splitext(args.out)[0] + ".json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    print(f"Saved {args.out} ({args.kind}; {meta['caption_hint'] or 'no error bars'}; font: {font or 'default'})")


if __name__ == "__main__":
    main()

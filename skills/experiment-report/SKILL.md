---
name: experiment-report
description: Turn raw experiment results (CSV, TSV or Excel files of runs, seeds, conditions, metrics or training logs) into a short, honest report with summary tables, statistics (mean, SD, 95% CI, Welch's t-test with Holm correction, effect size), publication-style figures that you visually check and fix before delivering, and a written summary where every number traces back to the data. Use this whenever the user wants to summarize, analyze, compare, plot, tabulate or write up experiment results, ablations, benchmark runs, multiple seeds, A/B conditions or learning curves, including requests like "실험 결과 정리해줘", "결과 표랑 그래프 만들어줘", "seed별 평균 내줘", "baseline이랑 비교해줘", "학습 곡선 그려줘", "summarize my results.csv", "make plots for my paper", even if they never say "report".
license: MIT
compatibility: Python 3.8+; matplotlib for figures; openpyxl only for .xlsx input.
---

# Experiment report

Researchers lose hours turning result logs into tables and figures, and that hand work is where errors creep in: a mistyped mean, a figure whose error bars mean nothing stated, a bar chart that hides a real difference, a crashed run silently averaged in. This skill does the mechanical part with scripts, so every number is computed rather than typed. You handle the parts that need judgment: which comparison matters, which figure answers it, whether the figure actually reads well, and what can honestly be claimed.

Scripts live in `${CLAUDE_SKILL_DIR}/scripts/`. If your agent does not substitute that variable, use the `scripts/` folder next to this SKILL.md. Use whichever Python is installed (`python3`, `python`, or `py -3`). Everything runs locally, and no data leaves the machine.

## Step 1: Look at the data first

```bash
python "${CLAUDE_SKILL_DIR}/scripts/summarize.py" results.csv --out experiment_report/profile
```

Without `--group` or `--metrics` this only profiles the table: columns, types, missing values, examples. It computes no statistics. CSV encodings common in Korean Excel exports (UTF-8 with BOM, CP949) are handled. Use `--sheet` to pick an Excel sheet.

From the profile, work out:
- **Condition columns**: what was varied, e.g. `method`, `model`, `dataset`.
- **Repeat columns**: what was repeated, e.g. `seed`, `fold`, `run`. These are not metrics. The script skips columns with ID-like names automatically and says so.
- **Metrics**: what was measured, and for each, whether higher or lower is better.
- **The baseline**, if there is one.

Ask the user only what you cannot infer, for example which metric is primary, or which group is the baseline when none is named "baseline". One short question beats a wrong report.

## Step 2: Compute the statistics

```bash
python "${CLAUDE_SKILL_DIR}/scripts/summarize.py" results.csv --group method --compare baseline --out experiment_report/all
```

- `--group` takes one or more comma-separated condition columns. Every combination becomes a group.
- `--compare REF` runs Welch's t-test of each group against REF, with a 95% CI of the difference and Cohen's d. `--pair "A:B"` (repeatable) adds other comparisons, e.g. between two proposed variants. All comparisons of one metric in one run are Holm-corrected together.
- `--filter dataset=A` restricts rows. Run once per dataset when results should not be pooled across datasets.
- `--exclude-rows 15` drops specific runs by their spreadsheet row number (header = row 1), for a with/without-outlier comparison.
- `--metrics a,b` picks metrics explicitly.
- **Learning curves:** to compare the end of training, filter to the last epoch (`--filter epoch=20 --metrics val_loss`). If the user cares about the best epoch instead, say which one you used.
- **Use a separate `--out` folder for every run** (`experiment_report/A`, `experiment_report/B`, `experiment_report/A_no_outlier`). The same folder would overwrite the previous `summary.json`.

Each run writes `summary.json` (every number, at full precision) and `summary.md` (the same as tables, one consistent rounding per metric). **The `summary.json` files are the only source for numbers in the report.** Copying beats recomputing: mental arithmetic and re-rounding are exactly how errors enter a hand-written report. Use the rounding shown in `summary.md`. If you need a number the script did not produce, compute it with code and say how.

Read the `notes` in the output and take each one seriously:
- *Missing values* were excluded. The note gives the row numbers; say how many, and where.
- *n < 3* means the CI and test are unreliable. Say so instead of reporting a p-value as if it meant something.
- *Possible outlier (Grubbs test)* is often a crashed or mis-logged run. Do not delete it silently. Report it, look at that row, and if excluding it is justified, re-run with `--exclude-rows` and show results both with and without it.
- *Very large Cohen's d* usually means a tiny SD. Lead with the raw difference and its CI.
- Tests from separate runs (e.g. per dataset) are not corrected together. If you make many tests overall, say so, or Holm-correct them all with `tableio.holm`.

## Step 3: Make the figures

```bash
python "${CLAUDE_SKILL_DIR}/scripts/plot.py" results.csv --kind point --x method --y accuracy --hue dataset --out experiment_report/figs/accuracy.png
```

Pick the kind that answers the question:

| Question | Kind | Notes |
|---|---|---|
| Which condition is best (final results)? | `point` or `bar` | `bar` must start at 0, so it hides small differences. The script prints a HINT when that happens; switch to `point`. |
| How spread out are the runs? | `box` | Shows every run as a dot. Good for timing and latency. |
| How does a metric evolve (epochs, steps, data size)? | `line` | Mean line with an error band across repeats. |
| Is there a trade-off between two metrics? | `scatter` | e.g. accuracy vs training time, coloured by method |

Other options: `--error ci95|sd|sem|none` (default 95% CI), `--order` to control group order (put the baseline first), `--ylabel` to add units (comma-separated, one per metric), `--xlabel`, `--rotate`, `--legend inside|outside|none`, `--filter`, `--exclude-rows`, `--logy`, `--ylim`. Several metrics in `--y` become side-by-side panels.

Each figure gets a small caption line ("error bars: 95% CI; n = 5 per group") and a sidecar `.json` with the same facts. Use them in the report caption.

## Step 4: Look at every figure before you show it

Open each PNG with your image-viewing ability and actually look. A script that runs without errors can still produce a figure that misleads or is unreadable, and only looking catches it. Check:

- Text renders properly. Korean labels shown as □□□ mean a missing font; the script picks Malgun Gothic, AppleGothic, NanumGothic or Noto Sans KR when installed.
- Tick labels do not overlap or get cut off. If they do, use `--rotate 30`, shorter group names, or `--width`.
- The legend does not cover data. If it does, use `--legend outside`.
- Axis labels say what is plotted, with units.
- The y axis does not exaggerate or hide differences. Bars must start at 0; if that hides everything, switch to `point`.
- Group order makes sense, with the baseline first.
- The figure matches the numbers in `summary.json`, for example which group is highest.

Fix with flags and re-render. Two or three rounds is normal. In the report, mention anything you changed for honesty reasons, such as switching from bars to points.

## Step 5: Write the report

Write `experiment_report/report.md` following `references/report-template.md`. Write in the user's language. Principles:

- **Every number comes from a `summary.json`**, with the same rounding as its `summary.md`. When there are several runs, make clear which subset each number is from (e.g. dataset A, without row 15).
- **Separate what the data shows from what it might mean.** "Method B's mean accuracy was 0.0287 higher (95% CI 0.0152–0.0421)" is a result. "B's augmentation probably helps generalization" is an interpretation; label it as such.
- **Significance claims need the corrected p-value and an effect size.** With several comparisons, use `p_holm`. With n of 3 to 5 seeds, prefer CIs and effect sizes over p-values, and say that n is small.
- **Report what didn't work and what's odd** (outliers, missing runs, a condition that got worse). That is where the user learns something.
- Keep it short. A results section, not a paper.

## Step 6: Hand over

In chat, give the 2–4 key findings in plain sentences and the paths to `report.md`, `summary.md` and the figures. Mention any judgment calls (outliers, which dataset was pooled) so the user can disagree.

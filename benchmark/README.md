# Benchmark: with skill vs without skill

This benchmark asks whether installing these skills actually changes the result. The same AI agent (headless Claude Code, same model) gets the same task twice. The only difference is whether the skills are loaded.

## What is held constant

| | Both conditions |
|---|---|
| Python | One shared virtual environment, `benchmark/.venv`, with pinned packages (`requirements.lock.txt`), first on `PATH` |
| Agent | `claude -p` (headless Claude Code), same model, same allowed tools (`Bash Read Write Edit Glob Grep WebFetch WebSearch Skill`) |
| Task | Same prompt (`tasks/*/prompt.md`) and same input files, copied into a fresh folder for every run |
| Timing | For each repetition, both conditions run at the same time, so public APIs (Crossref, arXiv, …) treat them alike |
| **Difference** | `skill` runs with `--plugin-dir <this repo>`; `baseline` runs without it |

## Tasks

**citation**: `tasks/citation/input/manuscript.md`, a Korean introduction with 10 references. These inputs were never used while building the skill. The references are 5 real papers, 1 real paper with a wrong year, 2 with a DOI or arXiv ID that points to a different paper, and 2 invented papers. Two citing sentences misstate their source. The agent must write `verdicts.csv`, and `grade.py citation` scores it against `answer_key.json`.

**experiment**: `tasks/experiment/input/`. It holds results for 3 methods × 2 datasets × 5 seeds in a CP949-encoded CSV with Korean headers, as Korean Excel saves it, plus a training log. Planted traps:
- a crashed run (accuracy 0.10) that makes one method look worse
- a missing value
- one comparison with no real difference
- a baseline that overfits after epoch 17

A reviewer who doesn't know which condition produced each report scores it on 14 items (`rubric.md`). `make_data.py` regenerates the data and the answer key.

## Reproduce

```bash
cd benchmark
./setup_env.sh            # or .\setup_env.ps1 on Windows
claude auth login         # headless Claude Code uses your Claude account
.venv/bin/python run_benchmark.py --reps 3          # Windows: .venv\Scripts\python run_benchmark.py --reps 3
.venv/bin/python grade.py citation
.venv/bin/python grade.py blind                     # then grade grading/R* with rubric.md -> grading/grades.json
.venv/bin/python grade.py aggregate                 # results/results.md
```

Each run takes a few minutes and uses your Claude plan's usage. Raw runs (transcripts, outputs) go to `runs/`, which is not committed. `results/` holds the summary.

## Notes on this run

- Model: `claude-opus-5` for both conditions, via Claude Code CLI 2.1.278 on Windows 11 with Python 3.14.7. Opus 5.5 needs CLI ≥ 2.1.280; to use it, run `claude update` and pass `--model claude-opus-5-5`.
- Answer key change after the pilot: reference [3] (an invented title carrying the real DOI of another paper) fits both `WRONG_ID` and `FAKE` as the prompt defines them, so both are accepted. The change applies to both conditions equally.
- Blinding is partial. The grader did not know which condition produced which report, but figure styles and file names can hint at it.

## Results

See [`results/results.md`](results/results.md).

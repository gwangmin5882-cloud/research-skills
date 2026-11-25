#!/usr/bin/env python3
"""
run_benchmark.py - with-skill vs without-skill comparison in one shared environment.

Both conditions run headless Claude Code (`claude -p`) with:
  - the same Python virtual environment (benchmark/.venv) first on PATH,
  - the same model, prompt, input files and allowed tools,
  - a fresh working folder per run.
The only difference: the `skill` condition loads this repository as a plugin
(`--plugin-dir`), the `baseline` condition does not.

Usage (from benchmark/, after `setup_env` and `claude auth login`):
  .venv/Scripts/python run_benchmark.py --reps 3                 # Windows
  .venv/bin/python run_benchmark.py --reps 3 --tasks citation    # macOS/Linux, one task
  python run_benchmark.py --reps 1 --start 2                     # add a 2nd repetition later

For every (repetition, task) the two conditions run at the same time, so they
see the same network conditions (public APIs rate-limit both alike).
Results go to runs/<task>/<condition>/run-<k>/ : the task files, whatever the agent
produced, transcript.jsonl (stream-json), and meta.json (time, turns, tokens, skill use).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TASKS = ["citation", "experiment"]
CONDITIONS = ["baseline", "skill"]
TOOLS = "Bash Read Write Edit Glob Grep WebFetch WebSearch Skill"


def venv_bin():
    for sub in ("Scripts", "bin"):
        p = os.path.join(HERE, ".venv", sub)
        if os.path.isdir(p):
            return p
    raise SystemExit("benchmark/.venv not found. Run setup_env.ps1 (Windows) or setup_env.sh first.")


def clean_env():
    """Environment shared by both conditions: venv first on PATH, no parent-session variables."""
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("CLAUDE") or k.startswith("ANTHROPIC") or k == "VIRTUAL_ENV")}
    vb = venv_bin()
    env["PATH"] = vb + os.pathsep + env.get("PATH", "")
    env["VIRTUAL_ENV"] = os.path.dirname(vb)
    return env


def claude_cmd():
    exe = shutil.which("claude.cmd") or shutil.which("claude")
    if not exe:
        raise SystemExit("claude (Claude Code CLI) not found on PATH.")
    return [exe]


def prepare(task, cond, k):
    run_dir = os.path.join(HERE, "runs", task, cond, f"run-{k}")
    if os.path.exists(run_dir):
        shutil.rmtree(run_dir)
    shutil.copytree(os.path.join(HERE, "tasks", task, "input"), run_dir)
    return run_dir


def start(task, cond, k, model, timeout_min):
    run_dir = prepare(task, cond, k)
    prompt = open(os.path.join(HERE, "tasks", task, "prompt.md"), encoding="utf-8").read()
    cmd = claude_cmd() + ["-p", "--output-format", "stream-json", "--verbose",
                          "--model", model, "--permission-mode", "acceptEdits",
                          "--allowedTools", TOOLS]
    if cond == "skill":
        cmd += ["--plugin-dir", REPO]
    out = open(os.path.join(run_dir, "transcript.jsonl"), "wb")
    err = open(os.path.join(run_dir, "stderr.txt"), "wb")
    p = subprocess.Popen(cmd, cwd=run_dir, env=clean_env(), stdin=subprocess.PIPE, stdout=out, stderr=err)
    p.stdin.write(prompt.encode("utf-8"))
    p.stdin.close()
    return {"task": task, "cond": cond, "k": k, "dir": run_dir, "proc": p, "t0": time.time(),
            "deadline": time.time() + timeout_min * 60, "files": (out, err)}


def summarize_transcript(path):
    meta = {"skill_invoked": False, "skill_script_used": False, "tool_calls": 0, "tools": {}}
    result = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "assistant":
                for block in (ev.get("message") or {}).get("content") or []:
                    if block.get("type") == "tool_use":
                        name = block.get("name")
                        meta["tool_calls"] += 1
                        meta["tools"][name] = meta["tools"].get(name, 0) + 1
                        inp = json.dumps(block.get("input") or {}, ensure_ascii=False)
                        if name == "Skill" and ("citation-check" in inp or "experiment-report" in inp):
                            meta["skill_invoked"] = True
                        if any(s in inp for s in ("check_refs.py", "summarize.py", "plot.py")):
                            meta["skill_script_used"] = True
            elif ev.get("type") == "result":
                result = ev
    if result:
        u = result.get("usage") or {}
        meta.update({
            "is_error": result.get("is_error"),
            "duration_s": round((result.get("duration_ms") or 0) / 1000, 1),
            "num_turns": result.get("num_turns"),
            "cost_usd_equivalent": result.get("total_cost_usd"),
            "input_tokens": u.get("input_tokens"),
            "cache_read_tokens": u.get("cache_read_input_tokens"),
            "cache_creation_tokens": u.get("cache_creation_input_tokens"),
            "output_tokens": u.get("output_tokens"),
            "final_text": result.get("result"),
        })
    return meta


def finish(run, status):
    for f in run["files"]:
        f.close()
    meta = summarize_transcript(os.path.join(run["dir"], "transcript.jsonl"))
    meta.update({"task": run["task"], "condition": run["cond"], "run": run["k"], "status": status,
                 "wall_s": round(time.time() - run["t0"], 1)})
    with open(os.path.join(run["dir"], "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    if meta.get("final_text"):
        with open(os.path.join(run["dir"], "answer.md"), "w", encoding="utf-8") as fh:
            fh.write(meta["final_text"])
    print(f"  done {run['task']}/{run['cond']}/run-{run['k']}: {status}, {meta['wall_s']}s, "
          f"turns={meta.get('num_turns')}, skill={meta['skill_invoked'] or meta['skill_script_used']}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--start", type=int, default=1, help="number of the first repetition")
    ap.add_argument("--tasks", default=",".join(TASKS))
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--timeout-min", type=float, default=25)
    args = ap.parse_args()
    tasks = [t for t in args.tasks.split(",") if t]

    info = {"model": args.model, "tools": TOOLS, "python": os.path.join(venv_bin(), "python"),
            "claude_version": subprocess.run(claude_cmd() + ["--version"], capture_output=True, text=True,
                                             env=clean_env()).stdout.strip(),
            "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    os.makedirs(os.path.join(HERE, "runs"), exist_ok=True)
    with open(os.path.join(HERE, "runs", "environment.json"), "w", encoding="utf-8") as fh:
        json.dump(info, fh, ensure_ascii=False, indent=2)
    print(json.dumps(info, ensure_ascii=False), flush=True)

    for k in range(args.start, args.start + args.reps):
        for task in tasks:
            print(f"[rep {k}] {task}: starting baseline and skill together", flush=True)
            runs = [start(task, c, k, args.model, args.timeout_min) for c in CONDITIONS]
            while runs:
                time.sleep(5)
                for r in list(runs):
                    if r["proc"].poll() is not None:
                        finish(r, "ok" if r["proc"].returncode == 0 else f"exit {r['proc'].returncode}")
                        runs.remove(r)
                    elif time.time() > r["deadline"]:
                        r["proc"].kill()
                        r["proc"].wait()
                        finish(r, "timeout")
                        runs.remove(r)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    main()

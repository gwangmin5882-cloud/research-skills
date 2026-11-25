#!/usr/bin/env sh
# Creates the shared Python environment for the benchmark (macOS / Linux).
# Usage:  ./setup_env.sh            (uses python3 on PATH)
#         ./setup_env.sh /path/to/python
# The venv goes to $BENCH_HOME/.venv when BENCH_HOME is set, otherwise next to this script.
PY="${1:-python3}"
HERE="$(cd "$(dirname "$0")" && pwd)"
HOME_DIR="${BENCH_HOME:-$HERE}"
mkdir -p "$HOME_DIR"
"$PY" -m venv "$HOME_DIR/.venv"
"$HOME_DIR/.venv/bin/python" -m pip install --upgrade pip
"$HOME_DIR/.venv/bin/python" -m pip install -r "$HERE/requirements.lock.txt"
"$HOME_DIR/.venv/bin/python" --version

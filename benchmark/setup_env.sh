#!/usr/bin/env sh
# Creates the shared Python environment for the benchmark (macOS / Linux).
# Usage:  ./setup_env.sh            (uses python3 on PATH)
#         ./setup_env.sh /path/to/python
PY="${1:-python3}"
"$PY" -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.lock.txt
./.venv/bin/python --version

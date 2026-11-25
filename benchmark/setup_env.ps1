# Creates the shared Python environment for the benchmark (Windows PowerShell).
# Usage:  .\setup_env.ps1            (uses `python` on PATH)
#         .\setup_env.ps1 C:\path\to\python.exe
param([string]$Python = "python")
& $Python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe --version

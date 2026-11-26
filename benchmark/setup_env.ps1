# Creates the shared Python environment for the benchmark (Windows PowerShell).
# Usage:  .\setup_env.ps1            (uses `python` on PATH)
#         .\setup_env.ps1 C:\path\to\python.exe
# The venv goes to $env:BENCH_HOME\.venv when BENCH_HOME is set, otherwise next to this script.
# Set BENCH_HOME to a short folder (e.g. C:\Users\you\rsb) if this repository sits deep in the
# file system: Windows can't load DLLs (Pillow, used by matplotlib) from paths over 260 characters.
param([string]$Python = "python")
$BenchHome = if ($env:BENCH_HOME) { $env:BENCH_HOME } else { $PSScriptRoot }
New-Item -ItemType Directory -Force $BenchHome | Out-Null
$Venv = Join-Path $BenchHome ".venv"
& $Python -m venv $Venv
$Py = Join-Path $Venv "Scripts\python.exe"
& $Py -m pip install --upgrade pip
& $Py -m pip install -r (Join-Path $PSScriptRoot "requirements.lock.txt")
& $Py --version

@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   RBC + Austin, TX Senior Finance AI Radar
echo ============================================================

if not exist ".venv\Scripts\python.exe" (
    echo [1/2] Creating local Python virtual environment...
    python -m venv .venv
    echo [2/2] Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip -q
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

set PYTHONIOENCODING=utf-8
echo Launching interactive local radar server at http://127.0.0.1:8787 ...
".venv\Scripts\python.exe" rbc_austin_radar.py --serve
pause

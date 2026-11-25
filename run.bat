@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   RBC + Austin, TX Senior Finance AI Radar
echo ============================================================

if not exist ".venv\Scripts\python.exe" (
    echo [1/2] Creating local Python virtual environment...
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        python -m venv .venv
    ) else (
        py -3 -m venv .venv
    )
    if not exist ".venv\Scripts\python.exe" (
        echo Python 3 was not found. Opening pre-loaded HTML snapshot in your browser instead...
        start "" "outputs\rbc_austin_ai_board.html"
        exit /b 0
    )
    echo [2/2] Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip -q
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Optional JobSpy build skipped; installing core requests scraper...
        ".venv\Scripts\python.exe" -m pip install "requests>=2.31.0"
    )
)

set PYTHONIOENCODING=utf-8
echo Launching interactive local radar server at http://127.0.0.1:8787 ...
".venv\Scripts\python.exe" rbc_austin_radar.py --serve
pause

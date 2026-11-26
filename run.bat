@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo   RBC + Austin, TX AI ^& Finance Job Radar
echo ============================================================

if not exist ".venv\Scripts\python.exe" goto :setup_venv
goto :run_app

:setup_venv
echo [1/2] Creating local Python virtual environment...
set "SYS_PY="

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 set "SYS_PY=python"

if not defined SYS_PY (
    py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
    if not errorlevel 1 set "SYS_PY=py -3"
)

if not defined SYS_PY (
    echo Python 3.10+ was not found. Opening pre-loaded HTML snapshot in your browser instead...
    start "" "outputs\rbc_austin_ai_board.html"
    exit /b 0
)

%SYS_PY% -m venv .venv
if errorlevel 1 goto :venv_failed
if not exist ".venv\Scripts\python.exe" goto :venv_failed
".venv\Scripts\python.exe" -m pip --version >nul 2>nul
if errorlevel 1 goto :venv_failed

echo [2/2] Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Optional JobSpy build skipped; installing core requests scraper...
    ".venv\Scripts\python.exe" -m pip install "requests>=2.31.0"
    if errorlevel 1 (
        echo Failed to install dependencies. Opening pre-loaded HTML snapshot instead...
        start "" "outputs\rbc_austin_ai_board.html"
        exit /b 1
    )
)
goto :run_app

:venv_failed
echo Failed to create a working virtual environment. Cleaning up partial .venv...
if exist ".venv" rmdir /s /q ".venv"
echo Opening pre-loaded HTML snapshot in your browser instead...
start "" "outputs\rbc_austin_ai_board.html"
exit /b 0

:run_app
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
echo Launching interactive local radar server at http://127.0.0.1:8787 ...
".venv\Scripts\python.exe" rbc_austin_radar.py --serve %*
set "APP_EXIT=!errorlevel!"
if "%~1"=="" pause
exit /b !APP_EXIT!

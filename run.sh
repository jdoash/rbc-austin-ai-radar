#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"

echo "============================================================"
echo "  RBC + Austin, TX AI & Finance Job Radar"
echo "============================================================"

if [ ! -x ".venv/bin/python" ]; then
    if ! command -v python3 >/dev/null 2>&1; then
        echo "Python 3 not found. Opening pre-loaded HTML snapshot in your browser instead..."
        open "outputs/rbc_austin_ai_board.html" 2>/dev/null || xdg-open "outputs/rbc_austin_ai_board.html" 2>/dev/null || true
        exit 0
    fi
    echo "[1/2] Creating local Python virtual environment..."
    python3 -m venv .venv
    echo "[2/2] Installing dependencies..."
    .venv/bin/python -m pip install --upgrade pip -q
    if ! .venv/bin/python -m pip install -r requirements.txt; then
        echo "Optional JobSpy build skipped; installing core requests scraper..."
        .venv/bin/python -m pip install "requests>=2.31.0"
    fi
fi

export PYTHONIOENCODING=utf-8
echo "Launching interactive local radar server at http://127.0.0.1:8787 ..."
.venv/bin/python rbc_austin_radar.py --serve

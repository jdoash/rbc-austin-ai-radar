#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "============================================================"
echo "  RBC + Austin, TX Senior Finance AI Radar"
echo "============================================================"

if [ ! -x ".venv/bin/python" ]; then
    echo "[1/2] Creating local Python virtual environment..."
    python3 -m venv .venv
    echo "[2/2] Installing dependencies..."
    .venv/bin/python -m pip install --upgrade pip -q
    .venv/bin/python -m pip install -r requirements.txt
fi

export PYTHONIOENCODING=utf-8
echo "Launching interactive local radar server at http://127.0.0.1:8787 ..."
.venv/bin/python rbc_austin_radar.py --serve

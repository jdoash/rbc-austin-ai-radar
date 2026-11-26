#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"

NO_OPEN=0
for arg in "$@"; do
    if [ "$arg" = "--no-open" ]; then
        NO_OPEN=1
    fi
done

echo "============================================================"
echo "  RBC + Austin, TX AI & Finance Job Radar"
echo "============================================================"

open_offline_snapshot() {
    if [ "$NO_OPEN" -eq 1 ]; then
        echo "Offline HTML snapshot available at: outputs/rbc_austin_ai_board.html"
        return 0
    fi
    if [ "$(uname -s)" = "Darwin" ] && command -v open >/dev/null 2>&1; then
        echo "Opening pre-loaded HTML snapshot in your browser instead..."
        open "outputs/rbc_austin_ai_board.html" 2>/dev/null || true
    elif command -v xdg-open >/dev/null 2>&1 && { [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; }; then
        echo "Opening pre-loaded HTML snapshot in your browser instead..."
        xdg-open "outputs/rbc_austin_ai_board.html" </dev/null >/dev/null 2>&1 &
    else
        echo "Open outputs/rbc_austin_ai_board.html in your browser to view the offline snapshot."
    fi
}

find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1; then
                echo "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

if [ ! -x ".venv/bin/python" ] || ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
    if [ -d ".venv" ]; then
        echo "Removing incomplete virtual environment..."
        rm -rf .venv
    fi
    SYS_PY="$(find_python || true)"
    if [ -z "$SYS_PY" ]; then
        echo "Python 3.10+ not found."
        open_offline_snapshot
        exit 0
    fi
    echo "[1/2] Creating local Python virtual environment with $SYS_PY..."
    if ! "$SYS_PY" -m venv .venv || [ ! -x ".venv/bin/python" ] || ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
        echo "Failed to create a working virtual environment (on Debian/Ubuntu, run: sudo apt install python3-venv)."
        rm -rf .venv
        open_offline_snapshot
        exit 1
    fi
    echo "[2/2] Installing dependencies..."
    .venv/bin/python -m pip install --upgrade pip -q
    if ! .venv/bin/python -m pip install -r requirements.txt; then
        echo "Optional JobSpy build skipped; installing core requests scraper..."
        if ! .venv/bin/python -m pip install "requests>=2.31.0"; then
            echo "Failed to install core requests dependency."
            open_offline_snapshot
            exit 1
        fi
    fi
fi

export PYTHONIOENCODING=utf-8
export PYTHONUNBUFFERED=1
echo "Launching interactive local radar server at http://127.0.0.1:8787 ..."
exec .venv/bin/python rbc_austin_radar.py --serve "$@"

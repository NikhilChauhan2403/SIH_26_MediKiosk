#!/usr/bin/env bash
# MediKiosk - Startup Script
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

VENV_PYTHON="/home/nish/.gemini/antigravity/scratch/venv/bin/python3"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="python3"
fi

echo "==========================================================="
echo "  MediKiosk: Smart Patient Case-Taking Software (SIH 2026)"
echo "  Ministry of Ayush / All India Institute of Ayurveda"
echo "==========================================================="

echo "[1/2] Verifying and seeding initial clinical database..."
"$VENV_PYTHON" -c "from backend.app.seed import seed_database; seed_database()"

echo "[2/2] Launching MediKiosk Server on http://localhost:8000 ..."
echo "      - Patient Kiosk:   http://localhost:8000"
echo "      - Doctor Portal:   http://localhost:8000#doctor"
echo "      - Interactive API: http://localhost:8000/docs"
echo "-----------------------------------------------------------"

exec "$VENV_PYTHON" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

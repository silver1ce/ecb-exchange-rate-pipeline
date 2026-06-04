#!/usr/bin/env bash
# Run the ECB pipeline locally without Docker (uses SQLite by default).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -q -e ".[dev]"

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

mkdir -p data

export PYTHONPATH=.
python scripts/init_db.py

echo ""
echo "Starting API at http://localhost:8000"
echo "Swagger docs: http://localhost:8000/docs"
echo "Press Ctrl+C to stop"
echo ""

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

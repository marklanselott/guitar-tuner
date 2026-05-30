#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -x ".venv/bin/python3" ]; then
  echo "Virtualenv not found. Create it first, then install requirements."
  exit 1
fi

cleanup() {
  pkill -P $$ -f "start.py" 2>/dev/null || true
  pkill -P $$ -f "arecord -D plughw" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

exec env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 start.py

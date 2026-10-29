#!/usr/bin/env bash
# No-memory pilot, in one command. Run inside the Codespace:
#     bash scripts/run_pilot.sh
# Checks the setup, runs one smoke task, runs all 19 tasks without memory,
# then commits and pushes runs/ so the results can be reviewed.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1/5 update code and dependencies"
git pull --rebase
pip install --user -q -r requirements.txt

echo "== 2/5 offline tests (no API calls)"
python -m pytest -q

echo "== 3/5 model connection"
python scripts/check_model.py

echo "== 4/5 smoke run: one real task"
python -m attest run --task E01 --name smoke

echo "== 5/5 pilot: all 19 tasks, no memory (about 10-15 minutes)"
python -m attest pilot --name pilot_nomem --parallel 4

git add runs
git commit -m "No-memory pilot: smoke run and all 19 tasks"
git push
echo "== done: results pushed"

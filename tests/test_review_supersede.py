"""D69: superseding rules is human-only, keeps the old note in the log, and removes it from retrieval."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_segregation_cases_all_behave_as_fixed(tmp_path):
    out = tmp_path / "seg"
    subprocess.run([sys.executable, str(ROOT / "scripts/segregation_eval.py"), "--out", str(out)], check=True, capture_output=True)
    import json
    r = json.loads((out / "results.json").read_text())
    assert r["passed"] == r["cases"], [x for x in r["rows"] if not x["pass"]]

import json
import re

from attest import report
from attest.benchmark import PROJECT_ROOT


def test_report_builds_from_a_real_run(tmp_path):
    out = report.build(PROJECT_ROOT / "runs" / "smoke", tmp_path / "index.html")
    html = out.read_text()
    assert "<title>Attest Experiment Report</title>" in html
    data = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
    assert data["meta"]["runs"] == 1
    run = data["runs"][0]
    assert run["task"] == "E01" and run["commands"] and "round_money" in run["diff"]
    assert [h["id"] for h in data["hypotheses"]] == ["H1", "H2", "H3", "H4", "H5", "H6"]

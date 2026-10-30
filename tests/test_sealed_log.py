"""Sealed event log (D42): chained, authenticated, verified on load, refused when tampered."""

import json

import pytest

from attest.memory.store import EventStore, TamperedLog, verify_events

KEY = b"canary-key"


def test_sealed_log_round_trip_and_tamper_detection(tmp_path):
    path = tmp_path / "events.jsonl"
    s = EventStore(path, seal_key=KEY)
    s.append("add", item={"id": "at-0001", "content": "Money is Decimal", "scope": {"repo": "ledgerly"}, "status": "active"})
    s.append("update", id="at-0001", fields={"status": "suspect"}, reason="r")
    head = s.head
    assert EventStore(path, seal_key=KEY, head=head).items()["at-0001"]["status"] == "suspect"
    lines = path.read_text().splitlines()
    e = json.loads(lines[0]); e["item"]["scope"]["repo"] = "simkit"
    path.write_text(json.dumps(e) + "\n" + lines[1] + "\n")
    with pytest.raises(TamperedLog):
        EventStore(path, seal_key=KEY)
    assert not verify_events([json.loads(lines[0])], KEY, head)["ok"]  # truncated: the anchored head no longer matches


def test_unsealed_logs_still_load():
    assert EventStore(None).append("add", item={"id": "x"})["seq"] == 1

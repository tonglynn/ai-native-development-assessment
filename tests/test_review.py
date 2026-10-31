"""Human review in the memory lifecycle (D62)."""

import pytest

from attest.memory.earned import EarnedMemory
from attest.memory.review import ReviewRefused, approve, policy_changed, queue, reject

APPROVERS = {"finance-lead@acme", "eng-lead@acme"}


def mem():
    m = EarnedMemory(None)
    item = {"id": "at-0001", "kind": "lesson", "type": "business_policy", "title": "Refunds above 500 need approved_by",
            "content": "Support refunds above 500.00 need approved_by.", "status": "active", "observed_only": True,
            "assessment": {"state": "uncertain", "counter": [], "hard": [], "soft": ["trusted reviewer"]},
            "scope": {"repo": "ledgerly", "observed_version": "1.0.0", "valid_from": "1.0.0", "valid_until": None, "files": []},
            "source": {"task_id": "E04", "review_comments": [], "references": [], "proposed_by": "agent:deepseek-flash"},
            "evidence": [], "supersedes": [], "superseded_by": None,
            "usage": {"shown": 0, "cited": 0, "cited_pass": 0, "cited_fail": 0, "fail_streak": 0}}
    m.store.append("add", item=item, reason="test")
    return m


def test_agents_and_strangers_cannot_approve():
    m = mem()
    with pytest.raises(ReviewRefused):
        approve(m, "at-0001", by="agent:deepseek-flash", reason="looks right", evidence=["x"], approvers=APPROVERS | {"agent:deepseek-flash"})
    with pytest.raises(ReviewRefused):
        approve(m, "at-0001", by="someone@acme", reason="ok", evidence=["x"], approvers=APPROVERS)


def test_approval_is_recorded_and_undone_by_a_policy_change():
    m = mem()
    assert [q["id"] for q in queue(m)] == ["at-0001"]
    approve(m, "at-0001", by="finance-lead@acme", reason="matches FIN-2026-03", evidence=["policy FIN-2026-03", "test_conv_c6_blocks_unapproved"],
            approvers=APPROVERS, scope={"valid_until": "2.0.0"})
    it = m.store.items()["at-0001"]
    assert it["assessment"]["state"] == "approved" and it["review"]["by"] == "finance-lead@acme"
    assert it["review"]["depends_on"] == ["FIN-2026-03"] and it["scope"]["valid_until"] == "2.0.0" and queue(m) == []
    policy_changed(m, "FIN-2026-03", by="finance-lead@acme", reason="FIN-2026-09 raises the threshold")
    it = m.store.items()["at-0001"]
    assert it["assessment"]["state"] == "uncertain" and it["review"]["superseded_by"] == "FIN-2026-03" and queue(m)


def test_reject_retires_with_record():
    m = mem()
    reject(m, "at-0001", by="eng-lead@acme", reason="not our policy", approvers=APPROVERS)
    it = m.store.items()["at-0001"]
    assert it["status"] == "retired" and it["review"]["decision"] == "rejected"
    with pytest.raises(ValueError):
        approve(m, "at-0001", by="eng-lead@acme", reason="changed my mind", evidence=["x"], approvers=APPROVERS)

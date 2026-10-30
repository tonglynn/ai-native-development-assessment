"""Liveness check of learned rules against code (scripts/liveness_check.py)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import liveness_check as lc  # noqa: E402

V1, V2 = ROOT / "benchmark/repos/ledgerly_v1", ROOT / "benchmark/repos/ledgerly_v2"
ROUND = {"title": "Round money only with round_money", "version": "1.0.0",
         "content": "Always round with ledgerly.money.round_money (half-up to the cent); never use round()."}
APPROVAL = {"title": "Refunds above 500.00 need approved_by", "version": "1.0.0",
            "content": "Support-initiated refunds above 500.00 need approved_by, else BillingError('approval_required')."}
BOOL = {"title": "Exclude bool", "version": "1.0.0", "content": "Reject `bool` first (`isinstance(x, bool)`)."}


def test_builtins_are_not_anchors_and_project_names_are():
    base = lc.corpus(V1)
    assert lc.anchors(lc.mentions(BOOL["content"]), base) == []
    assert {"round_money", "half-up"} <= set(lc.anchors(lc.mentions(ROUND["content"]), base))


def test_versions_and_changelog():
    base = lc.corpus(V1)
    assert lc.status(ROUND, base, base)["status"] == "alive"
    on_v2 = lc.status(ROUND, base, lc.corpus(V2))
    assert on_v2["status"] == "drifted" and on_v2["missing"] == ["half-up"]  # v2 rounds half-even
    assert lc.status(APPROVAL, base, lc.corpus(V2))["status"] == "review"  # the changelog names 500.00
    assert lc.status(BOOL, base, base)["status"] == "not checkable"


def test_a_silent_rename_is_detected(tmp_path):
    base = lc.corpus(V1)
    renamed = lc.corpus(lc.renamed_copy(V1, tmp_path / "copy"))
    note = {"title": "Normalize datetimes with ensure_utc", "version": "1.0.0", "content": "Use `ensure_utc` from ledgerly.clock."}
    assert lc.status(note, base, renamed)["missing"] == ["ensure_utc"]

"""Optional general notes and reserved slots for repository-wide rules (D46)."""

from types import SimpleNamespace

from attest.memory import earned
from attest.memory.earned import EarnedMemory

DIFF = """--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -1,1 +1,2 @@
 # Changelog
+- Added `voucherDetails` to `CheckoutError`.
--- a/saleor/order/tests/test_calc.py
+++ b/saleor/order/tests/test_calc.py
@@ -1,1 +1,2 @@
 x = 1
+@pytest.mark.parametrize("status", ["a", "b"])
"""
RUN = {"first_pass": False, "final_pass": True, "attempts": [{"review_comments": ["Please add a CHANGELOG entry.", "Could we parametrise it?"]}]}
WIDE = {"kind": "lesson", "title": "Add a CHANGELOG entry", "content": "Every user-facing change needs a CHANGELOG.md entry.",
        "evidence_quote": "Please add a CHANGELOG entry.", "applied_in_diff": "Added `voucherDetails` to `CheckoutError`.",
        "example": "CHANGELOG.md for voucherDetails", "breadth": "repository"}
LOCAL = {"kind": "lesson", "title": "Parametrise order calculation tests", "content": "Parametrise tests of order calculation statuses.",
         "evidence_quote": "Could we parametrise it?", "applied_in_diff": '@pytest.mark.parametrize("status", ["a", "b"])',
         "example": "saleor/order/tests/test_calc.py", "breadth": "weird"}


def task(i, title):
    return SimpleNamespace(id=i, title=title, issue=title, repo_name="saleor")


def test_general_fields_stored_and_reserved_slot(monkeypatch):
    monkeypatch.setattr(earned.llm, "complete_json", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    m = EarnedMemory(None, general=True, reserved=2)
    m.learn(task("PR#1", "x"), "main", RUN, "", DIFF, candidates=[WIDE, LOCAL])
    items = m.store.items()
    assert items["at-0001"]["breadth"] == "repository" and items["at-0002"]["breadth"] == "local"  # unknown -> local
    r = m.retrieve(task("PR#2", "order calculation statuses parametrise"), "main")
    assert r.ids[0] == "at-0001" and "at-0002" in r.ids and "(example: CHANGELOG.md for voucherDetails)" in r.context
    off = EarnedMemory(None)
    off.learn(task("PR#1", "x"), "main", RUN, "", DIFF, candidates=[WIDE, LOCAL])
    assert "breadth" not in off.store.items()["at-0001"] and off.name == "attest" and m.name == "attest_general"

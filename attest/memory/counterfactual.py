"""Counterfactual check (D59): a test validates a note only if it depends on the note's change.

R2 (D57) counted "the source task's tests of this convention passed" as independent validation. On the
frozen judgement set from an empty memory, that let 5 of 10 wrong pieces of advice become rules: the
tests passed, but they never checked the wrong claim. The counterfactual version asks the question a
reviewer would: take the verified workspace, revert the note's change, and run the tests again.

  validated     every test passes with the change, and at least one test of a convention the note is
                about fails without it
  not validated the tests pass either way (they do not depend on the change), or only tests of other
                conventions fail
  inconclusive  the reverted workspace does not import or the tests cannot be collected; never validates
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


def apply(text: str, replacements) -> str:
    for old, new in replacements:
        if old not in text:
            raise ValueError(f"replacement target not found: {old[:60]!r}")
        text = text.replace(old, new, 1)
    return text


def conv_failures(result: dict, conventions: set[str]) -> list[str]:
    return [h["name"] for h in result["hidden"] if not h["passed"]
            and any(f"conv_{c.lower()}" in h["name"] for c in conventions)]


def check(task, workspace: Path, file: str, revert, conventions: set[str]) -> dict:
    """Run the task's tests on the workspace and on a copy with `revert` applied to `file`."""
    from ..verify import verify
    after = verify(workspace, task)
    with tempfile.TemporaryDirectory() as tmp:
        rev = Path(tmp) / "ws"
        shutil.copytree(workspace, rev)
        target = rev / file
        target.write_text(apply(target.read_text(), revert))
        before = verify(rev, task)
    collected = bool(before["hidden"]) and not any("collect" in (h.get("name") or "") for h in before["hidden"])
    failing = conv_failures(before, conventions)
    status = ("invalid: tests fail with the change" if not after["passed"] else
              "inconclusive: reverted workspace does not run" if not collected else
              "validated" if failing else "not validated: the tests do not depend on the change")
    return {"status": status, "validated": status == "validated", "after_passed": after["passed"],
            "reverted_conv_failures": failing,
            "reverted_other_failures": [h["name"] for h in before["hidden"] if not h["passed"] and h["name"] not in failing]}

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


def auto_revert(source: str, applied: str) -> tuple[str, str] | None:
    """Derive the counterfactual edit for the statement the note's applied line belongs to.

    simple statement (assignment, call, raise, return, ...)  remove it (`pass` keeps the block valid)
    `if` header whose body rejects (raise / return)          remove the whole check: the claim is "reject when"
    `if` header whose body acts                              keep the body, drop the condition: the claim is
                                                             "do this only when"
    Returns (old_text, new_text) to apply to the file, or None when no statement can be found."""
    import ast
    import textwrap
    lines = source.splitlines(keepends=True)
    target = " ".join(applied.split())
    idx = next((i for i, ln in enumerate(lines) if target and target in " ".join(ln.split())), None)
    if idx is None:
        return None
    tree = ast.parse(source)
    best = None
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and node.lineno - 1 <= idx <= node.end_lineno - 1:
            if best is None or (node.end_lineno - node.lineno) < (best.end_lineno - best.lineno):
                best = node
    if best is None:
        return None
    if isinstance(best, ast.If) and best.lineno - 1 == idx and not best.orelse:
        old = "".join(lines[best.lineno - 1: best.end_lineno])
        indent = lines[best.lineno - 1][: len(lines[best.lineno - 1]) - len(lines[best.lineno - 1].lstrip())]
        rejects = all(isinstance(b, (ast.Raise, ast.Return)) for b in best.body)
        if rejects:
            return old, indent + "pass\n"
        body = "".join(lines[best.body[0].lineno - 1: best.body[-1].end_lineno])
        return old, textwrap.indent(textwrap.dedent(body), indent)
    old = "".join(lines[best.lineno - 1: best.end_lineno])
    indent = lines[best.lineno - 1][: len(lines[best.lineno - 1]) - len(lines[best.lineno - 1].lstrip())]
    return old, indent + "pass\n"


def counterfactuals(source: str, applied: str, note_text: str) -> list[tuple[str, str]]:
    """Every counterfactual edit for the note's applied line: the statement-level one (auto_revert) and,
    for each call in the line whose function the note names, the call replaced by its first argument
    (float(amount) -> amount, ensure_utc(at) -> at). The note is validated only if EVERY one of them makes
    a test of its conventions fail: a claim about a sub-expression is not validated by the statement."""
    import ast
    import re
    from .evidence import code_names
    edits = []
    stmt = auto_revert(source, applied)
    if stmt:
        edits.append(stmt)
    named = code_names(note_text) | {w.lower() for w in re.findall(r"\b[A-Za-z_][A-Za-z_0-9]*\b", note_text)}
    lines = source.splitlines(keepends=True)
    target = " ".join(applied.split())
    idx = next((i for i, ln in enumerate(lines) if target and target in " ".join(ln.split())), None)
    if idx is None:
        return edits
    for node in ast.walk(ast.parse(source)):  # calls on the applied line, inside whatever statement holds it
        if isinstance(node, ast.Call) and node.args and node.lineno - 1 == idx and node.end_lineno - 1 == idx:
            fn = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if fn.lower() in named and not isinstance(node.func, ast.Attribute):
                call, arg = ast.get_source_segment(source, node), ast.get_source_segment(source, node.args[0])
                if call and arg and call in lines[idx]:
                    edits.append((lines[idx], lines[idx].replace(call, arg, 1)))
    return edits


def check_all(task, workspace: Path, file: str, edits, conventions: set[str]) -> dict:
    """Validated only if the change passes and every counterfactual edit breaks a test of the conventions."""
    if not edits:
        return {"status": "inconclusive: no counterfactual edit", "validated": False, "edits": []}
    results = [check(task, workspace, file, [e], conventions) for e in edits]
    ok = all(r["validated"] for r in results)
    return {"status": "validated" if ok else next(r["status"] for r in results if not r["validated"]),
            "validated": ok, "after_passed": results[0]["after_passed"], "edits": [r["status"] for r in results]}

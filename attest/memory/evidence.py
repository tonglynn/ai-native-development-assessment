"""Typed evidence for Attest's write gate.

A candidate note must show two different things, recorded separately:

  source   where the rule comes from: a verbatim excerpt of a review comment (or of
           the diff), plus any policy / incident references it names (FIN-2026-03,
           INC-204, ...). This proves someone asked for it; it does not prove it is right.
  applied  where the accepted change does it: a changed line of the diff, typed by
           the kind of file (code, test, doc, config) and by the change (added or
           removed). This proves it was actually done, not just said.

Verification (did the change pass) is recorded as a third, separate field by the
caller: passing tests show the code meets the tests, not that the rule is correct.

Matching is line-based and tolerant of what models get wrong when copying (diff
markers, whitespace, a few missing words), but every line of the claimed snippet
must be found in one changed line of the diff, so a rule nobody applied still
cannot be "applied".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

REFERENCE_RE = re.compile(r"\b(?:INC|FIN|SEC|POL|ADR|RFC|CVE)-\d[\d-]*\d\b")
WORD_RE = re.compile(r"[A-Za-z0-9_]+")

DOC_SUFFIXES = (".md", ".rst", ".txt", ".adoc")
CONFIG_SUFFIXES = (".toml", ".cfg", ".ini", ".yaml", ".yml", ".json")


@dataclass
class ChangedLine:
    file: str
    change: str  # "added" | "removed"
    text: str


def file_kind(path: str) -> str:
    name = path.rsplit("/", 1)[-1].lower()
    if path.startswith("tests/") or "/tests/" in path or name.startswith("test_") or name.endswith("_test.py"):
        return "test"
    if name.endswith(DOC_SUFFIXES) or path.startswith("docs/") or name.startswith(("changes", "changelog", "readme")):
        return "doc"
    if name.endswith(CONFIG_SUFFIXES):
        return "config"
    return "code"


def parse_diff(diff: str) -> list[ChangedLine]:
    """Changed lines of a unified diff, with the file each belongs to."""
    out, current = [], ""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[4:].strip()
            current = current[2:] if current.startswith(("a/", "b/")) else current
            continue
        if line.startswith("--- ") or line.startswith("diff --git") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            out.append(ChangedLine(current, "added", line[1:]))
        elif line.startswith("-"):
            out.append(ChangedLine(current, "removed", line[1:]))
    return out


def strip_markers(text: str) -> str:
    """Remove unified-diff markers at line starts (models often copy them into snippets)."""
    return "\n".join(line[1:] if line[:1] in "+- " and not line.startswith(("+++", "---")) else line
                     for line in (text or "").splitlines())


def normalise(text: str) -> str:
    return " ".join((text or "").split()).lower()


def sides(diff: str) -> tuple[str, str]:
    """The diff's before and after text (context plus removed / added lines), so a quote copied
    from either version of a file is contiguous even where the diff interleaves - and + lines."""
    before, after = [], []
    for line in diff.splitlines():
        if line.startswith(("+++", "---", "diff --git", "@@")):
            before.append("")
            after.append("")
        elif line.startswith("+"):
            after.append(line[1:])
        elif line.startswith("-"):
            before.append(line[1:])
        else:
            text = line[1:] if line.startswith(" ") else line
            before.append(text)
            after.append(text)
    return "\n".join(before), "\n".join(after)


def source_corpus(review_comments: list[str], diff: str) -> str:
    before, after = sides(diff)
    return normalise("\n".join(review_comments)) + " \u241e " + normalise(before) + " \u241e " + normalise(after)


def references(*texts: str) -> list[str]:
    return sorted({m.group(0) for t in texts for m in REFERENCE_RE.finditer(t or "")})


def _words(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(text or "")]


def _line_matches(claim: str, actual: str) -> bool:
    c, a = normalise(claim), normalise(actual)
    if len(c) >= 10 and c in a:
        return True
    words = _words(claim)
    if len(words) < 3:
        return False
    have = set(_words(actual))
    return sum(w in have for w in words) / len(words) >= 0.8


def find_applied(snippet: str, changed: list[ChangedLine], allow_removed: bool = True) -> dict | None:
    """The changed line(s) of the diff that the claimed snippet refers to, typed; None if not found.

    Each non-empty line of the snippet must match one changed line (verbatim substring
    of at least 10 characters, or at least 80% of its words, at least 3 words)."""
    lines = [ln.strip() for ln in strip_markers(snippet).splitlines() if ln.strip()]
    if not lines or len(normalise(" ".join(lines))) < 10:
        return None
    pool = [c for c in changed if allow_removed or c.change == "added"]
    found = []
    for claim in lines:
        hit = next((c for c in pool if _line_matches(claim, c.text)), None)
        if hit is None:
            return None
        found.append(hit)
    first = found[0]
    return {"kind": file_kind(first.file), "change": first.change, "file": first.file,
            "line": first.text.strip()[:200], "lines_matched": len(found)}

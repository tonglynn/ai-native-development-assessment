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

Matching is line-based and tolerates only format differences in copying (diff
markers, whitespace, case, omitted tokens): every token of a claimed line must occur,
in order, in one real line of the diff, and the lines must follow the diff's order.
Paraphrases, synonyms, swapped operators and reordered lines are rejected, and the
evidence must be a changed line (see find_applied), so a rule nobody applied still
cannot be "applied".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

REFERENCE_RE = re.compile(r"\b(?:INC|FIN|SEC|POL|ADR|RFC|CVE)-\d[\d-]*\d\b")
# Tokens: identifiers, numbers with their sign, and operators as tokens of their own, so a claim with
# "<" for ">", "-1" for "1" or "!ok" for "ok" does not match (re-checks r8, D27 m2). Omitting a token
# is still allowed (D25).
WORD_RE = re.compile(r"-?\d+(?:\.\d+)?|[A-Za-z_][A-Za-z0-9_]*|->|=>|<<|>>|//|\*\*|&&|\|\||[<>=!]=|\+=|-=|[<>=!+\-*/%]")

DOC_SUFFIXES = (".md", ".rst", ".txt", ".adoc")
CONFIG_SUFFIXES = (".toml", ".cfg", ".ini", ".yaml", ".yml", ".json")


@dataclass
class ChangedLine:
    file: str
    change: str  # "added" | "removed" | "context" (unchanged; never evidence on its own)
    text: str
    hunk: int = 0  # index of the @@ hunk, so context is only accepted next to its own change


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
    """Lines of a unified diff (added, removed, and unchanged context), with the file each belongs to."""
    out, current, hunk = [], "", 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[4:].strip()
            current = current[2:] if current.startswith(("a/", "b/")) else current
            hunk += 1
            continue
        if line.startswith("@@"):
            hunk += 1
            continue
        if line.startswith("--- ") or line.startswith("diff --git"):
            continue
        if line.startswith("+"):
            out.append(ChangedLine(current, "added", line[1:], hunk))
        elif line.startswith("-"):
            out.append(ChangedLine(current, "removed", line[1:], hunk))
        elif line.startswith(" "):
            out.append(ChangedLine(current, "context", line[1:], hunk))
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
    """Format tolerance only, never paraphrase (D21, bounded in D25).

    A claimed line matches a real changed line if, after removing diff markers and
    normalising whitespace and case, it is a verbatim substring of at least 10
    characters, or its words (at least 3) all occur in the real line in the same
    order, so the claim may only *omit* words. A word that is not in the line, a
    synonym or a reordering never matches."""
    c, a = normalise(claim), normalise(actual)
    if len(c) >= 10 and c in a:
        return True
    words = _words(claim)
    if len(words) < 3:
        return False
    rest = iter(_words(actual))
    return all(any(w == x for x in rest) for w in words)  # ordered subsequence


def _short(claim: str) -> bool:
    return len(_words(claim)) < 3 and len(normalise(claim)) < 10


def find_applied(snippet: str, changed: list[ChangedLine], allow_removed: bool = True) -> dict | None:
    """The changed line the claimed snippet refers to, typed; None if not found.

    Rules (D25, D27, re-check of D27):
    - Every claimed line must be a real line of the diff (_line_matches: format tolerance only), and the
      lines must appear in the diff's order. A line is skipped only if it has no token at all (e.g. ")").
    - A line too short for the word rule (fewer than 3 tokens and under 10 characters) must equal a
      diff line exactly, and can never be the evidence.
    - Evidence is a changed (added, or removed) line that passes on its own. At least one is needed,
      and changed lines must be at least half of the claimed lines.
    - Unchanged context lines may surround the evidence only in the same file and hunk as an evidence
      line, so an unchanged line elsewhere (e.g. an existing `audit.clear()`) can never carry the rule.
    - Only the first evidence line is recorded, and it is always the real diff line, not the claim.
    The gate does not check that the evidence line is *about* the rule (relevance is not verified)."""
    lines = [ln.strip() for ln in strip_markers(snippet).splitlines() if ln.strip()]
    lines = [ln for ln in lines if _words(ln)]
    if not lines or len(normalise(" ".join(lines))) < 10:
        return None
    usable = [c for c in changed if c.change != "removed" or allow_removed]

    def ok(claim, c):
        if _short(claim):
            return normalise(c.text) == normalise(claim)
        return _line_matches(claim, c.text)

    found, start = [], 0  # (claim, diff line), searched in diff order
    for claim in lines:
        idx = next((i for i in range(start, len(usable)) if ok(claim, usable[i])), None)
        if idx is None:
            return None
        found.append((claim, usable[idx]))
        start = idx + 1
    evidence = [c for claim, c in found if c.change != "context" and not _short(claim)]
    changes = [c for _, c in found if c.change != "context"]
    if not evidence or len(changes) * 2 < len(found):
        return None
    hunks = {(c.file, c.hunk) for c in evidence}
    if any(c.change == "context" and (c.file, c.hunk) not in hunks for _, c in found):
        return None
    first = evidence[0]
    return {"kind": file_kind(first.file), "change": first.change, "file": first.file,
            "line": first.text.strip()[:200], "lines_matched": len(changes)}


# Relevance of the applied line (optional, after the four-case gate experiment, D37): the gate
# checks that the cited line is a real changed line, not that it is about the rule, so a note can
# cite an unrelated line of the same change. With relevance on, when the evidence quote names
# code (a call, a dotted name, a snake_case identifier or backticked code), the applied line must
# contain one of those names. Quotes that name no code cannot be checked and pass.
_CODE_RE = re.compile(r"`([^`]+)`|\b([A-Za-z_]\w*)\(|\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)\b|\b([a-z]+_[a-z0-9_]+)\b")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def code_names(text: str) -> set[str]:
    names = set()
    for m in _CODE_RE.finditer(text or ""):
        frag = next(g for g in m.groups() if g)
        names |= {t.lower() for t in _IDENT_RE.findall(frag) if len(t) >= 3}
    return names


def applied_is_relevant(quote: str, applied_line: str) -> bool | None:
    """True/False if the quote names code; None if it names none (nothing to check)."""
    names = code_names(quote)
    if not names:
        return None
    return bool(names & {t.lower() for t in _IDENT_RE.findall(applied_line or "")})

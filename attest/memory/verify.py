"""Just-in-time verification of notes against the code (after GitHub Copilot's agentic memory).

At retrieval, each note chosen for injection is checked against the checkout the agent will
work on: do the project names it mentions still exist, and does a changelog entry newer
than the version it was learned on mention it? Copilot's agents re-read a memory's cited code
before using it; here the check is deterministic, and its result is shown to the agent next to
the note ("check before use"), so the agent re-reads the code instead of trusting the note.

Anchors (what is checked): names the note mentions that the project defines at the version
the note was learned on (functions, classes, module constants, module names, file paths) and
domain terms found in that code ("half-up" in ROUND_HALF_UP). Python builtins are not anchors.
  drifted        an anchor is missing from the current code
  review         a newer changelog entry names one of the note's names, terms or amounts
  alive          every anchor is present and no newer entry mentions it
  not checkable  no anchor and no mention
"alive" means the names a rule mentions still exist, not that the rule still holds
(RESULTS.md, forgetting V2 point 5).
"""

from __future__ import annotations

import ast
import re
from functools import lru_cache
from pathlib import Path

from ..benchmark import REPOS_DIR, repo_version
from .earned import EarnedMemory


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _version_tuple(v: str) -> tuple:
    return tuple(int(x) if x.isdigit() else 0 for x in v.split("."))


@lru_cache(maxsize=16)
def corpus(repo: Path, package: str = "ledgerly") -> dict:
    defined, idents, files = set(), set(), set()
    for p in sorted((repo / package).rglob("*.py")):
        rel = p.relative_to(repo).as_posix()
        files.add(rel)
        defined.add(p.stem)
        tree = ast.parse(p.read_text())
        for node in tree.body:
            if isinstance(node, ast.Assign):
                defined |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                defined.add(node.name)
            elif isinstance(node, ast.Name):
                idents.add(node.id)
            elif isinstance(node, ast.Attribute):
                idents.add(node.attr)
    entries = []
    log = repo / "CHANGELOG.md"
    for block in re.split(r"^## ", log.read_text() if log.exists() else "", flags=re.M)[1:]:
        m = re.match(r"(\d+\.\d+\.\d+)", block)
        if m:
            entries.append((m.group(1), block))
    return {"defined": frozenset(defined), "norm_idents": frozenset(norm(i) for i in idents | defined),
            "files": frozenset(files), "changelog": tuple(entries)}


def mentions(text: str) -> dict:
    ids = set()
    for span in re.findall(r"`([^`]+)`", text):
        ids |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", span))
    for dotted in re.findall(r"\b[a-z_]+(?:\.[a-z_]+)+\b", text):
        ids |= set(dotted.split("."))
    ids |= set(re.findall(r"\b[a-z]+_[a-z0-9_]+\b", text))
    ids |= set(re.findall(r"\b[A-Z][a-z]+[A-Z][A-Za-z]+\b", text))
    ids |= set(re.findall(r"\b[A-Z][A-Z0-9_]{2,}\b", text))
    return {"ids": ids, "terms": set(re.findall(r"\b[a-z]+-[a-z]+\b", text, re.I)),
            "amounts": set(re.findall(r"\b\d+\.\d{2}\b", text)), "paths": set(re.findall(r"ledgerly/\w+\.py", text))}


def anchors(m: dict, base: dict) -> list[str]:
    out = {i for i in m["ids"] if i in base["defined"]}
    out |= {p for p in m["paths"] if p in base["files"]}
    out |= {t for t in m["terms"] if len(norm(t)) >= 5 and any(norm(t) in i for i in base["norm_idents"])}
    return sorted(out)


def present(anchor: str, c: dict) -> bool:
    if anchor.endswith(".py"):
        return anchor in c["files"]
    if anchor in c["defined"]:
        return True
    return "-" in anchor and any(norm(anchor) in i for i in c["norm_idents"])


def status(note: dict, base: dict, current: dict, first_run_matching: bool = False) -> dict:
    """Verdict of one note (title, content, version) learned on `base`, checked against `current`."""
    m = mentions(f"{note['title']} {note['content']}")
    anc = anchors(m, base)
    missing = [a for a in anc if not present(a, current)]
    newer = [text for v, text in current["changelog"] if _version_tuple(v) > _version_tuple(note["version"])]
    if first_run_matching:  # the first liveness run (kept for the record, RESULTS.md)
        words = {i for i in m["ids"] if len(i) >= 4} | m["terms"] | m["amounts"]
        changed = sorted(w for w in words if any(norm(w) in norm(t) for t in newer) and len(norm(w)) >= 4)
    else:  # project names except module names (also plain words, e.g. "money"), terms, amounts; whole words
        modules = {Path(f).stem for f in base["files"]}
        words = {i for i in m["ids"] if i in base["defined"] and i not in modules} | m["terms"] | m["amounts"]
        changed = sorted(w for w in words if any(re.search(rf"(?<![\w.]){re.escape(w)}(?![\w])", t, re.I) for t in newer))
    s = "drifted" if missing else "review" if changed else "alive" if anc else "not checkable"
    return {"status": s, "anchors": anc, "missing": missing, "changelog_mentions": changed}


def repo_for(package: str, version: str) -> Path | None:
    for d in sorted(REPOS_DIR.iterdir()):
        if (d / package).is_dir() and repo_version(d) == version:
            return d
    return None


def verify(item: dict, task) -> dict:
    """Check a stored note against the task's checkout."""
    sc = item.get("scope") or {}
    package = sc.get("repo") or "ledgerly"
    current_dir = REPOS_DIR / task.repo
    if not (current_dir / package).is_dir():
        return {"status": "not checkable", "anchors": [], "missing": [], "changelog_mentions": []}
    base_dir = repo_for(package, sc.get("observed_version") or "") or current_dir
    return status({"title": item["title"], "content": item["content"], "version": sc.get("observed_version") or "0"},
                  corpus(base_dir, package), corpus(current_dir, package))


def warning(v: dict, item: dict) -> str | None:
    seen = (item.get("scope") or {}).get("observed_version")
    if v["status"] == "drifted":
        return (f"  CHECK BEFORE USE: this note was learned on {seen}; {', '.join(v['missing'])} no longer appears in this "
                "checkout's code. Read the current code and follow it where it disagrees with the note.")
    if v["status"] == "review":
        return (f"  CHECK BEFORE USE: CHANGELOG.md entries newer than {seen} mention {', '.join(v['changelog_mentions'])}. "
                "Read them and follow them where they disagree with the note.")
    return None


def citation(item: dict) -> str | None:
    """Where the note was applied, from its latest evidence: file and changed line."""
    for ev in reversed(item.get("evidence") or []):
        applied = ev.get("applied") or {}
        if applied.get("file") and applied.get("line"):
            return f"  cited code: {applied['file']}: `{applied['line'].strip()[:160]}` (re-read it before relying on the note)"
    return None


class VerifiedMemory(EarnedMemory):
    """Attest with just-in-time verification at retrieval.

    mode "annotate": every chosen note is checked; drifted and review notes are injected with a
    "check before use" line. mode "drop": drifted notes are excluded instead (review notes
    annotated). Eligibility (scope, versions, status) is checked first, as always."""

    def __init__(self, store_dir, *, mode: str = "annotate", cite: bool = False, write_back: bool = False, **kw):
        """cite (D40): show each injected note's evidence (file and changed line) so the agent can re-read
        the code itself, as Copilot's memories carry code citations. write_back (D40): store the verdict
        on the note; a drifted note becomes suspect, so the check is not repeated from scratch."""
        super().__init__(store_dir, **kw)
        assert mode in ("annotate", "drop"), mode
        self.mode, self.cite, self.write_back = mode, cite, write_back
        self.name = f"attest_verify_{mode}" + ("_cite" if cite else "") + ("_writeback" if write_back else "")

    def _exclusion(self, item, task, version):
        why = super()._exclusion(item, task, version)
        if why or self.mode != "drop":
            return why
        v = verify(item, task)
        return f"cited code changed: {', '.join(v['missing'])} missing" if v["status"] == "drifted" else ""

    def retrieve(self, task, repo_version):
        r = super().retrieve(task, repo_version)
        items = self.store.items()
        verdicts = {i: verify(items[i], task) for i in r.ids}
        lines, out = r.context.splitlines(), []
        current = None
        for line in lines:
            m = re.match(r"- \[([\w-]+)\]", line)
            if m:
                current = m.group(1)
            out.append(line)
            if current and line.startswith("  (learned from"):
                if self.cite and current in items:
                    c = citation(items[current])
                    if c:
                        out.append(c)
                w = warning(verdicts.get(current, {}), items[current]) if current in verdicts else None
                if w:
                    out.append(w)
        r.context = "\n".join(out)
        r.debug["verification"] = {i: v["status"] for i, v in verdicts.items()}
        if self.write_back:
            for i, v in verdicts.items():
                prev = (items[i].get("verification_check") or {})
                check = {"version": repo_version, "status": v["status"], "missing": v["missing"], "changelog_mentions": v["changelog_mentions"]}
                if prev == check:
                    continue
                fields = {"verification_check": check}
                reason = f"checked against {task.repo} ({repo_version}): {v['status']}"
                if v["status"] == "drifted" and items[i]["status"] == "active":
                    fields["status"] = "suspect"
                    reason += f"; {', '.join(v['missing'])} no longer in the code, marked suspect"
                self.store.append("update", id=i, fields=fields, reason=reason)
        return r

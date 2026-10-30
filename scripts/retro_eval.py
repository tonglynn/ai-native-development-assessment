"""Retrospective evaluation on real code-review history, judged by an independent model.

Merged, reviewed pull requests of a public repository are ordered by merge date.
Each memory system learns from the earlier ones (train). For every later PR
(test), we ask: which of the reviewers' comments would the notes it recalls have
anticipated, and which recalled notes were relevant at all?

A different model than the one that distills memory acts as the judge
(deepseek-v4-pro vs deepseek-flash). Notes are anonymised (N1, N2, ...) and
shuffled, so the judge cannot tell which system wrote them.

  coverage  = convention-type review comments anticipated by a recalled note / all convention-type comments
  precision = recalled notes the judge found relevant to the PR / all recalled notes

Usage (needs GITHUB_TOKEN and DEEPSEEK_API_KEY; runs in GitHub Actions):
    python scripts/retro_eval.py --repo pallets/flask --prs 60 --out runs/retro_flask
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from attest import llm  # noqa: E402
from attest.github_reviews import reviewed_merged_prs  # noqa: E402
from attest.memory import make_memory  # noqa: E402

JUDGE = "deepseek/deepseek-v4-pro"
SYSTEMS = ("attest", "reasoningbank", "ace")

CLASSIFY = """You read the review comments a maintainer left on one pull request of an open-source project.
For each numbered comment decide its kind:
  "convention" - expresses a reusable rule or preference of this project that would apply to other pull requests
                 (for example: changelog or docs requirements, API or typing style, testing practice, naming, structure);
  "specific"   - only about this pull request's particular logic, a typo, a question, thanks, or a one-off decision.
Return JSON: {"comments": [{"i": <number>, "kind": "convention" | "specific", "rule": "<the rule in one line, or empty>"}]}"""

ANTICIPATE = """A developer was about to open the pull request below. Before writing it, they were shown the NOTES.
Then maintainers left the REVIEW COMMENTS listed.
1. For each review comment, list the notes that, had the developer followed them, would have made the comment unnecessary
   (empty list if none). Be strict: a note anticipates a comment only if it states the same rule.
2. For each note, say whether it was relevant to this pull request (following it would matter for this change).
Return JSON: {"comments": [{"i": <number>, "anticipated_by": ["N1", ...]}], "notes": [{"n": "N1", "relevant": true | false}]}"""


def note_texts(memory, ids: list[str]) -> list[str]:
    items = memory.store.items()
    out = []
    for i in ids:
        it = items[i]
        title = it.get("title") or it.get("section") or ""
        out.append(f"{title}: {it.get('content', '')}".strip(": "))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="pallets/flask")
    ap.add_argument("--prs", type=int, default=60)
    ap.add_argument("--test-frac", type=float, default=0.35)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    name = args.repo.split("/")[1]
    args.out.mkdir(parents=True, exist_ok=True)

    prs = reviewed_merged_prs(args.repo, args.prs)
    n_test = max(1, round(len(prs) * args.test_frac))
    train, test = prs[:-n_test], prs[-n_test:]
    print(f"{len(prs)} reviewed PRs: train {len(train)}, test {len(test)}", flush=True)

    systems = {s: make_memory(s, args.out / s) for s in SYSTEMS}
    for pr in train:
        task = SimpleNamespace(id=f"PR#{pr['number']}", title=pr["title"], issue=f"{pr['title']}\n\n{pr['body']}", repo_name=name)
        run = {"first_pass": False, "final_pass": True, "verified_by": "merged by the maintainers", "shown_notes": [], "cited_notes": [],
               "attempts": [{"passed": False, "review_comments": pr["comments"]}]}
        for s, memory in systems.items():
            memory.learn(task, "main", run, "", pr["diff"])
        print(f"learned from PR#{pr['number']}: " + ", ".join(f"{s}={len(m.store.items())}" for s, m in systems.items()), flush=True)

    rng = random.Random(0)
    per_pr = []
    totals = {s: {"conv": 0, "covered": 0, "shown": 0, "relevant": 0} for s in SYSTEMS}
    lines = write_summary(args, prs, train, test, systems, totals, per_pr)
    for pr in test:
        numbered = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(pr["comments"]))
        kinds = llm.complete_json(CLASSIFY, f"PULL REQUEST: {pr['title']}\n\nREVIEW COMMENTS:\n{numbered}", model=JUDGE, thinking="on")
        conv = [k["i"] for k in kinds.get("comments", []) if k.get("kind") == "convention"]
        row = {"pr": pr["number"], "url": pr["url"], "title": pr["title"], "comments": len(pr["comments"]),
               "convention_comments": conv, "rules": [k.get("rule", "") for k in kinds.get("comments", []) if k.get("kind") == "convention"]}
        task = SimpleNamespace(id=f"PR#{pr['number']}", title=pr["title"], issue=f"{pr['title']}\n\n{pr['body']}", repo_name=name)
        for s, memory in systems.items():
            ids = memory.retrieve(task, "main").ids
            texts = note_texts(memory, ids)
            order = list(range(len(texts)))
            rng.shuffle(order)
            labels = {f"N{k + 1}": ids[j] for k, j in enumerate(order)}
            notes_block = "\n".join(f"N{k + 1}. {texts[j]}" for k, j in enumerate(order)) or "(no notes)"
            covered, relevant = 0, 0
            if conv and texts:
                conv_block = "\n".join(f"{i}. {pr['comments'][i - 1]}" for i in conv if 0 < i <= len(pr["comments"]))
                verdict = llm.complete_json(ANTICIPATE, f"PULL REQUEST: {pr['title']}\n{pr['body'][:800]}\n\nNOTES:\n{notes_block}\n\nREVIEW COMMENTS:\n{conv_block}", model=JUDGE, thinking="on")
                covered = sum(bool(c.get("anticipated_by")) for c in verdict.get("comments", []) if c.get("i") in conv)
                relevant = sum(bool(n.get("relevant")) for n in verdict.get("notes", []) if n.get("n") in labels)
                row[s] = {"shown": ids, "covered": covered, "relevant": relevant,
                          "anticipated": [{"i": c.get("i"), "by": [labels.get(n, n) for n in c.get("anticipated_by", [])]}
                                          for c in verdict.get("comments", []) if c.get("anticipated_by")]}
            elif texts:
                verdict = llm.complete_json(ANTICIPATE, f"PULL REQUEST: {pr['title']}\n{pr['body'][:800]}\n\nNOTES:\n{notes_block}\n\nREVIEW COMMENTS:\n(none of convention type)", model=JUDGE, thinking="on")
                relevant = sum(bool(n.get("relevant")) for n in verdict.get("notes", []) if n.get("n") in labels)
                row[s] = {"shown": ids, "covered": 0, "relevant": relevant, "anticipated": []}
            else:
                row[s] = {"shown": [], "covered": 0, "relevant": 0, "anticipated": []}
            t = totals[s]
            t["conv"] += len(conv)
            t["covered"] += covered
            t["shown"] += len(ids)
            t["relevant"] += relevant
        per_pr.append(row)
        print(json.dumps({k: row[k] for k in ("pr", "comments")} | {"convention": len(conv)} |
                         {s: (row[s]["covered"], len(row[s]["shown"]), row[s]["relevant"]) for s in SYSTEMS}), flush=True)
        # Written after every PR, so a cancelled or timed-out run still leaves a (partial) summary.
        lines = write_summary(args, prs, train, test, systems, totals, per_pr)
    print("\n".join(lines))


def write_summary(args, prs, train, test, systems, totals, per_pr) -> list[str]:
    summary = []
    for s in SYSTEMS:
        t = totals[s]
        summary.append({"system": s, "notes_stored": len(systems[s].store.items()),
                        "convention_comments": t["conv"], "anticipated": t["covered"],
                        "coverage": t["covered"] / t["conv"] if t["conv"] else None,
                        "notes_shown": t["shown"], "relevant": t["relevant"],
                        "precision": t["relevant"] / t["shown"] if t["shown"] else None})
    done = len(per_pr)
    (args.out / "results.json").write_text(json.dumps({"repo": args.repo, "train": len(train), "test": len(test),
                                                       "evaluated": done, "judge": JUDGE, "summary": summary,
                                                       "per_pr": per_pr}, indent=2) + "\n")
    status = "" if done == len(test) else f" **Partial: {done} of {len(test)} test PRs evaluated.**"
    lines = [f"# Retrospective evaluation on {args.repo}", "",
             f"{len(prs)} merged PRs with reviewer comments; learned from the oldest {len(train)}, evaluated on the newest {len(test)}. "
             f"Judge: {JUDGE}; memory distilled by deepseek/deepseek-flash; notes anonymised and shuffled.{status}", "",
             "| System | Notes stored | Convention comments | Anticipated | Coverage | Notes shown | Relevant | Precision |",
             "|---|---|---|---|---|---|---|---|"]
    for r in summary:
        cov = "–" if r["coverage"] is None else f"{r['coverage']:.0%}"
        prec = "–" if r["precision"] is None else f"{r['precision']:.0%}"
        lines.append(f"| {r['system']} | {r['notes_stored']} | {r['convention_comments']} | {r['anticipated']} | {cov} | {r['notes_shown']} | {r['relevant']} | {prec} |")
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    return lines


if __name__ == "__main__":
    main()

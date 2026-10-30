"""Case study: learn from real code review on a public GitHub repository.

For merged pull requests that reviewers commented on (oldest first), Attest gets
the PR title and description, the reviewers' comments and the merged diff, and
decides what to remember. "Verified" here means merged by the maintainers.
ReasoningBank-style memory receives the same input, for comparison.
The report keeps note texts, short evidence quotes and PR links, not the
comment threads themselves.

Usage (needs GITHUB_TOKEN and DEEPSEEK_API_KEY; runs in GitHub Actions):
    python scripts/ingest_github_reviews.py --repo pallets/flask --prs 40 --out runs/case_flask
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from attest.github_reviews import gh, reviewed_merged_prs  # noqa: E402
from attest.memory import make_memory  # noqa: E402

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="pallets/flask")
    ap.add_argument("--prs", type=int, default=40)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    name = args.repo.split("/")[1]
    args.out.mkdir(parents=True, exist_ok=True)

    prs = reviewed_merged_prs(args.repo, args.prs)
    systems = {cond: make_memory(cond, args.out / cond) for cond in ("attest", "reasoningbank")}
    log = []
    for pr in prs:
        diff = pr["diff"]
        task = SimpleNamespace(id=f"PR#{pr['number']}", title=pr["title"], issue=f"{pr['title']}\n\n{pr['body']}", repo_name=name)
        run = {"first_pass": False, "final_pass": True, "verified_by": "merged by the maintainers", "shown_notes": [], "cited_notes": [],
               "attempts": [{"passed": False, "review_comments": pr["comments"]}]}
        entry = {"pr": pr["number"], "url": pr["url"], "title": pr["title"], "review_comments": len(pr["comments"])}
        for cond, memory in systems.items():
            events = memory.learn(task, "main", run, "", diff)
            entry[cond] = {"added": sum(e["type"] == "add" for e in events),
                           "rejected": [e["reason"] for e in events if e["type"] == "reject"]}
        log.append(entry)
        print(json.dumps(entry), flush=True)

    open_issues = [i for i in gh(f"/repos/{args.repo}/issues", state="open", per_page=30) if "pull_request" not in i][:3]
    report = [f"# Case study: learning from code review on {args.repo}", "",
              f"{len(prs)} merged pull requests with reviewer comments, oldest first. "
              "Verified = merged by the maintainers. Real data; nothing simulated.", ""]
    for cond, memory in systems.items():
        items = memory.store.items()
        rejected = [e for e in memory.store.events if e["type"] == "reject"]
        report += [f"## {cond}: {len(items)} notes kept, {len(rejected)} candidates rejected", ""]
        for it in items.values():
            src = (it.get("source") or {}).get("task_id", "")
            ev = (it.get("evidence") or [{}])[0]
            quote = (ev.get("source") or {}).get("quote") or ev.get("quote", "")
            report.append(f"- `{it['id']}` ({src}) **{it.get('title', '')}**: {it['content']}"
                          + (f"  \n  evidence: “{quote[:160]}”" if quote else ""))
        if rejected:
            reasons = {}
            for e in rejected:
                reasons[e["reason"]] = reasons.get(e["reason"], 0) + 1
            report += ["", "Rejected candidates by reason:"] + [f"- {n}× {r}" for r, n in sorted(reasons.items(), key=lambda x: -x[1])]
        report.append("")
    report += ["## What would be recalled for open issues", ""]
    for issue in open_issues:
        task = SimpleNamespace(id=f"issue#{issue['number']}", title=issue["title"], issue=f"{issue['title']}\n{(issue['body'] or '')[:800]}", repo_name=name)
        report += [f"### [{issue['title']}]({issue['html_url']})", ""]
        for cond, memory in systems.items():
            shown = memory.retrieve(task, "main")
            report.append(f"- **{cond}**: {', '.join(shown.ids) or 'nothing'}")
        report.append("")
    (args.out / "report.md").write_text("\n".join(report) + "\n")
    (args.out / "prs.json").write_text(json.dumps(log, indent=2) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()

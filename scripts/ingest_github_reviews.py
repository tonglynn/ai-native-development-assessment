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
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from attest.memory import make_memory  # noqa: E402

API = "https://api.github.com"


def gh(path: str, accept: str = "application/vnd.github+json", **params):
    headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    for _ in range(3):
        resp = requests.get(f"{API}{path}", headers=headers, params=params, timeout=30)
        if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
            time.sleep(30)
            continue
        resp.raise_for_status()
        return resp.text if accept.endswith("diff") else resp.json()
    raise RuntimeError(f"GitHub API kept refusing {path}")


def reviewed_merged_prs(repo: str, limit: int) -> list[dict]:
    found = []
    for page in range(1, 11):
        for pr in gh(f"/repos/{repo}/pulls", state="closed", sort="updated", direction="desc", per_page=50, page=page):
            if not pr.get("merged_at") or pr["user"]["type"] == "Bot":
                continue
            author = pr["user"]["login"]
            comments = [c["body"] for c in gh(f"/repos/{repo}/pulls/{pr['number']}/comments", per_page=100)
                        if c["user"]["login"] != author and c["user"]["type"] != "Bot" and c["body"].strip()]
            comments += [r["body"] for r in gh(f"/repos/{repo}/pulls/{pr['number']}/reviews", per_page=100)
                         if r["user"] and r["user"]["login"] != author and r["user"]["type"] != "Bot" and (r["body"] or "").strip()]
            if not comments:
                continue
            found.append({"number": pr["number"], "title": pr["title"], "body": (pr["body"] or "")[:1500],
                          "url": pr["html_url"], "merged_at": pr["merged_at"], "comments": [c[:1200] for c in comments[:12]]})
            if len(found) >= limit:
                return sorted(found, key=lambda p: p["merged_at"])
    return sorted(found, key=lambda p: p["merged_at"])


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
        diff = gh(f"/repos/{args.repo}/pulls/{pr['number']}", accept="application/vnd.github.v3.diff")
        if len(diff) > 120_000:
            log.append({"pr": pr["number"], "skipped": "diff too large"})
            continue
        task = SimpleNamespace(id=f"PR#{pr['number']}", title=pr["title"], issue=f"{pr['title']}\n\n{pr['body']}", repo_name=name)
        run = {"first_pass": False, "final_pass": True, "shown_notes": [], "cited_notes": [],
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
            quote = (it.get("evidence") or [{}])[0].get("quote", "")
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

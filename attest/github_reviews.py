"""Fetch merged pull requests with reviewer comments from a public GitHub repository.

Used by the real-repository case study and the retrospective evaluation. Needs
network access to api.github.com (GitHub Actions; a GITHUB_TOKEN raises the
rate limit).
"""

from __future__ import annotations

import os
import time

import requests

API = "https://api.github.com"


def gh(path: str, accept: str = "application/vnd.github+json", **params):
    headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    for attempt in range(4):
        resp = requests.get(f"{API}{path}", headers=headers, params=params, timeout=30)
        if resp.status_code in (403, 429) and (resp.headers.get("X-RateLimit-Remaining") == "0" or "rate limit" in resp.text.lower()):
            time.sleep(20 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.text if accept.endswith("diff") else resp.json()
    raise RuntimeError(f"GitHub API kept refusing {path}")


def _reviewer_comments(repo: str, number: int, author: str) -> list[str]:
    def keep(user, body):
        return user and user["login"] != author and user["type"] != "Bot" and (body or "").strip()

    inline = [c["body"] for c in gh(f"/repos/{repo}/pulls/{number}/comments", per_page=100) if keep(c["user"], c["body"])]
    reviews = [r["body"] for r in gh(f"/repos/{repo}/pulls/{number}/reviews", per_page=100) if keep(r["user"], r["body"])]
    return [c.strip()[:1200] for c in inline + reviews][:15]


def reviewed_merged_prs(repo: str, limit: int, max_diff: int = 120_000) -> list[dict]:
    """Merged PRs that reviewers (not the author, not bots) commented on, oldest first, with their diffs."""
    seen, found = set(), []
    for review_state in ("changes_requested", "approved", "none"):
        for page in range(1, 6):
            q = f"repo:{repo} is:pr is:merged review:{review_state}"
            items = gh("/search/issues", q=q, sort="updated", order="desc", per_page=100, page=page).get("items", [])
            time.sleep(2)  # search API allows 30 requests per minute
            if not items:
                break
            for it in items:
                number = it["number"]
                if number in seen or it["user"]["type"] == "Bot":
                    continue
                seen.add(number)
                comments = _reviewer_comments(repo, number, it["user"]["login"])
                if not comments:
                    continue
                pr = gh(f"/repos/{repo}/pulls/{number}")
                diff = gh(f"/repos/{repo}/pulls/{number}", accept="application/vnd.github.v3.diff")
                if len(diff) > max_diff:
                    continue
                found.append({"number": number, "title": it["title"], "body": (it.get("body") or "")[:1500],
                              "url": it["html_url"], "merged_at": pr.get("merged_at") or "", "comments": comments, "diff": diff})
                if len(found) >= limit:
                    return sorted(found, key=lambda p: p["merged_at"])
    return sorted(found, key=lambda p: p["merged_at"])

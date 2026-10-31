"""Fetch merged pull requests with reviewer comments from a public GitHub repository.

Used by the real-repository case study and the retrospective evaluation. Needs
network access to api.github.com and a GITHUB_TOKEN (GitHub Actions provides one).

One GraphQL query returns 50 pull requests together with their reviews and
review comments, so finding reviewed PRs costs a handful of requests instead of
two per PR; only the diffs of selected PRs are fetched separately. A time budget
stops the search instead of letting it wait on rate limits indefinitely.
"""

from __future__ import annotations

import os
import time

import requests

API = "https://api.github.com"

QUERY = """
query($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: 50, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number title body url mergedAt
        author { login __typename }
        reviews(first: 20) {
          nodes {
            body
            author { login __typename }
            comments(first: 30) { nodes { body author { login __typename } } }
          }
        }
      }
    }
  }
}
"""


def _headers(accept: str = "application/vnd.github+json") -> dict:
    headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    return headers


def gh(path: str, accept: str = "application/vnd.github+json", **params):
    for attempt in range(3):
        resp = requests.get(f"{API}{path}", headers=_headers(accept), params=params, timeout=30)
        if resp.status_code in (403, 429) and "rate limit" in resp.text.lower():
            time.sleep(15 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.text if accept.endswith("diff") else resp.json()
    raise RuntimeError(f"GitHub API kept refusing {path}")


def _graphql(variables: dict) -> dict:
    resp = requests.post(f"{API}/graphql", json={"query": QUERY, "variables": variables}, headers=_headers(), timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]["search"]


def _human(actor: dict | None, author: str) -> bool:
    return bool(actor) and actor.get("login") != author and actor.get("__typename") != "Bot" and not actor.get("login", "").endswith("[bot]")


def reviewed_merged_prs(repo: str, limit: int, max_diff: int = 120_000, budget_seconds: int = 900) -> list[dict]:
    """Merged PRs that reviewers (not the author, not bots) commented on, oldest first, with their diffs."""
    started = time.time()
    found, cursor = [], None
    q = f"repo:{repo} is:pr is:merged sort:created-desc"
    while len(found) < limit and time.time() - started < budget_seconds:
        page = _graphql({"q": q, "cursor": cursor})
        for pr in page["nodes"]:
            if not pr or not pr.get("number"):
                continue
            author = (pr.get("author") or {}).get("login", "")
            if (pr.get("author") or {}).get("__typename") == "Bot":
                continue
            comments = []
            for review in pr["reviews"]["nodes"]:
                if _human(review.get("author"), author) and (review.get("body") or "").strip():
                    comments.append(review["body"].strip())
                for c in review["comments"]["nodes"]:
                    if _human(c.get("author"), author) and (c.get("body") or "").strip():
                        comments.append(c["body"].strip())
            if not comments:
                continue
            try:
                diff = gh(f"/repos/{repo}/pulls/{pr['number']}", accept="application/vnd.github.v3.diff")
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 406:  # GitHub refuses diffs that are too large
                    continue
                raise
            if len(diff) > max_diff:
                continue
            found.append({"number": pr["number"], "title": pr["title"], "body": (pr.get("body") or "")[:1500],
                          "url": pr["url"], "merged_at": pr.get("mergedAt") or "",
                          "comments": [c[:1200] for c in comments][:15], "diff": diff})
            print(f"found PR#{pr['number']} ({len(comments)} reviewer comments), {len(found)}/{limit}", flush=True)
            if len(found) >= limit:
                break
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return sorted(found, key=lambda p: p["merged_at"])

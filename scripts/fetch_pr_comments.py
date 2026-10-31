"""Re-fetch the reviewer comments and changed files of the PRs a retro run used (for its funnel).

The retro run (scripts/retro_eval.py) stored its results and the memories, not the training PRs'
comments. This fetches them again by number, with the same filter (human reviewers other than the
author, no bots, at most 15 comments of 1200 characters), using the REST API. Order inside a PR can
differ from the GraphQL order of the original run; edits made on GitHub since then cannot be undone.

Usage (needs GITHUB_TOKEN): python scripts/fetch_pr_comments.py --run runs/retro_saleor --out runs/retro_saleor_funnel
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from attest.github_reviews import gh  # noqa: E402


def human(user: dict | None, author: str) -> bool:
    return bool(user) and user.get("login") != author and user.get("type") != "Bot" and not user.get("login", "").endswith("[bot]")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    res = json.loads((args.run / "results.json").read_text())
    repo = res["repo"]
    train = [int(n) for n in re.findall(r"learned from PR#(\d+)", (args.run / "console.log").read_text())]
    test = [r["pr"] for r in res["per_pr"]]
    out = {}
    for n in train + test:
        pr = gh(f"/repos/{repo}/pulls/{n}")
        author = pr["user"]["login"]
        comments = [r["body"].strip() for r in gh(f"/repos/{repo}/pulls/{n}/reviews", per_page=100)
                    if human(r.get("user"), author) and (r.get("body") or "").strip()]
        comments += [c["body"].strip() for c in gh(f"/repos/{repo}/pulls/{n}/comments", per_page=100)
                     if human(c.get("user"), author) and (c.get("body") or "").strip()]
        files = [f["filename"] for f in gh(f"/repos/{repo}/pulls/{n}/files", per_page=100)]
        out[str(n)] = {"number": n, "split": "train" if n in train else "test", "title": pr["title"],
                       "body": (pr.get("body") or "")[:1500], "comments": [c[:1200] for c in comments][:15], "files": files}
        print(n, out[str(n)]["split"], len(comments), len(files), flush=True)
    (args.out / "prs.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()

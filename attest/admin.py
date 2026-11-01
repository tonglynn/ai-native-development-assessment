"""What only a person may do with an MCP repository's memory: list every note and retract one.

    python -m attest.admin notes   --repo PATH
    python -m attest.admin retract --repo PATH --note at-0001 --reason "..."
    python -m attest.admin review  --repo PATH                      (what waits for a person)
    python -m attest.admin approve --repo PATH --note at-0003 --by owner:finance-lead --reason "..." [--evidence "..."]
    python -m attest.admin reject  --repo PATH --note at-0003 --by owner:finance-lead --reason "..."
Approvers are the names in ATTEST_APPROVERS.

Same functions as ``python -m attest notes/retract``, but this module imports only the MCP server, so it
runs where only the MCP server's dependencies are installed (the Windows demo machine: mcp and pytest).
``python -m attest`` also imports the experiment runner and failed there. Deliberately not an MCP tool.
"""
from __future__ import annotations

import argparse
import json
import sys

from . import mcp_server


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m attest.admin")
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("notes", help="every note for the repository, retired ones included")
    n.add_argument("--repo", required=True)
    r = sub.add_parser("retract", help="a person withdraws a note (kept in the log as retired)")
    r.add_argument("--repo", required=True)
    r.add_argument("--note", required=True)
    r.add_argument("--reason", required=True)
    for name in ("review", "approve", "reject"):
        q = sub.add_parser(name)
        q.add_argument("--repo", required=True)
        if name != "review":
            q.add_argument("--note", required=True)
            q.add_argument("--by", required=True)
            q.add_argument("--reason", required=True)
        if name == "approve":
            q.add_argument("--evidence", action="append", help="what the approval relies on (default: the reason)")
    args = p.parse_args(argv)
    if args.cmd == "notes":
        notes = mcp_server.list_notes(args.repo, include_inactive=True)
        for note in notes:
            print(f"{note['id']}  [{note['status']}]  {note['title']}: {note['content']}")
        if not notes:
            print("no notes for this repository")
    elif args.cmd == "retract":
        print(json.dumps(mcp_server.retract(args.repo, args.note, args.reason), ensure_ascii=False))
    else:
        import os
        from .memory import review
        memory = mcp_server._memory(mcp_server._identity(args.repo)[3])
        approvers = {a.strip() for a in os.environ.get("ATTEST_APPROVERS", "").split(",") if a.strip()}
        if args.cmd == "review":
            waiting = review.queue(memory)
            for w in waiting:
                print(f"{w['id']}  [{w['state']}]  {w['title']}: {w['content']}\n    evidence: {w['evidence'][0]['quote'] if w['evidence'] else ''}"
                      f"\n    why not decided automatically: hard {w['hard'] or 'none'}, soft {w['soft'] or 'none'}, counter {w['counter'] or 'none'}")
            if not waiting:
                print("nothing waits for review")
        else:
            try:
                if args.cmd == "approve":
                    e = review.approve(memory, args.note, by=args.by, reason=args.reason, evidence=args.evidence or [args.reason], approvers=approvers)
                else:
                    e = review.reject(memory, args.note, by=args.by, reason=args.reason, approvers=approvers)
            except (review.ReviewRefused, KeyError, ValueError) as exc:
                print(f"refused: {exc}")
                return 1
            print(e["reason"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

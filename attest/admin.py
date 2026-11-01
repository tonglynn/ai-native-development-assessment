"""What only a person may do with an MCP repository's memory: list every note and retract one.

    python -m attest.admin notes   --repo PATH
    python -m attest.admin retract --repo PATH --note at-0001 --reason "..."

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
    args = p.parse_args(argv)
    if args.cmd == "notes":
        notes = mcp_server.list_notes(args.repo, include_inactive=True)
        for note in notes:
            print(f"{note['id']}  [{note['status']}]  {note['title']}: {note['content']}")
        if not notes:
            print("no notes for this repository")
    else:
        print(json.dumps(mcp_server.retract(args.repo, args.note, args.reason), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

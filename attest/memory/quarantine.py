"""Quarantine and propagation trace for a note found to be wrong or malicious (D45; optional).

Retraction says "this note is wrong". After a poisoning or injection incident one also needs to
know where it went: which tasks were shown it, which of them did what it said, and which other
notes were learned in tasks that had seen it (and may carry it on). This module answers that from
the event log and the per-task result files, and quarantines: the note is withheld from retrieval
(like retired), kept with who and why, and the notes learned downstream of it can be held for
review too. Human-only, like retract: not exposed through MCP.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def quarantine(memory, item_id: str, by: str, reason: str, downstream: list[str] = ()) -> list[dict]:
    """Withhold a note (status quarantined) and hold the notes learned downstream of it for review."""
    items = memory.store.items()
    if item_id not in items:
        raise KeyError(item_id)
    events = [memory.store.append("update", id=item_id, fields={"status": "quarantined", "quarantined_by": by},
                                  reason=f"quarantined by {by}: {reason}")]
    for d in downstream:
        if d in items and items[d]["status"] in ("active", "suspect"):
            events.append(memory.store.append("update", id=d, fields={"status": "pending_review", "held_because": item_id},
                                              reason=f"held for review: learned in a task that was shown {item_id}"))
    return events


def trace(events: list[dict], results: Path, item_id: str, applied: re.Pattern | None = None) -> dict:
    """Where a note came from and where it went.

    origin         the event that added it (task, evidence quote, applied line)
    confirmations  later tasks that added evidence to it
    exposed        tasks whose injected notes included it (from result.json)
    obeyed         exposed tasks whose final diff adds a line matching ``applied``
    downstream     other notes added or confirmed in an exposed task (they may carry it on)
    """
    origin = next((e for e in events if e["type"] == "add" and e["item"]["id"] == item_id), None)
    confirmations = [e["reason"] for e in events if e["type"] == "update" and e.get("id") == item_id
                     and "evidence" in (e.get("fields") or {})]
    exposed, obeyed = [], []
    for res in sorted(Path(results).glob("*/result.json")):
        r = json.loads(res.read_text())
        if item_id in (r.get("injected_notes") or []):
            exposed.append(r["task_id"])
            diff = (res.parent / "final.diff").read_text() if (res.parent / "final.diff").exists() else ""
            if applied is not None and any(applied.search(x) for x in diff.splitlines() if x.startswith("+") and not x.startswith("+++")):
                obeyed.append(r["task_id"])
    downstream = set()
    for e in events:
        tid = (e.get("item") or {}).get("source", {}).get("task_id") if e["type"] == "add" else None
        if e["type"] == "update" and "evidence" in (e.get("fields") or {}):
            tid = (e["fields"]["evidence"][-1] or {}).get("task_id")
        nid = e["item"]["id"] if e["type"] == "add" else e.get("id")
        if tid in exposed and nid != item_id:
            downstream.add(nid)
    return {"note": item_id,
            "origin": None if origin is None else {"task": origin["item"]["source"]["task_id"],
                                                   "quote": origin["item"]["evidence"][0]["source"]["quote"],
                                                   "applied": (origin["item"]["evidence"][0].get("applied") or {}).get("line")},
            "confirmations": len(confirmations), "exposed": exposed, "obeyed": obeyed, "downstream": sorted(downstream)}

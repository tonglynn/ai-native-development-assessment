"""Append-only event log. The current state of every memory item is derived by replaying events.

Nothing is ever deleted or edited in place, so every status change keeps its
reason and evidence: the log *is* the audit trail of the memory.

Event types:
  add      {"item": {...}}                         a new item
  update   {"id", "fields": {...}, "reason"}       shallow update (status, counters, evidence ...)
  reject   {"candidate": {...}, "reason"}          a candidate that did not pass the write gate
"""

from __future__ import annotations

import copy
import json
import threading
import time
from pathlib import Path


class EventStore:
    def __init__(self, path: Path | None):
        self.path = path
        self._lock = threading.Lock()
        self._events: list[dict] = []
        if path and path.exists():
            self._events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def append(self, event_type: str, **payload) -> dict:
        event = {"seq": len(self._events) + 1, "ts": round(time.time(), 3), "type": event_type, **payload}
        with self._lock:
            self._events.append(event)
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a") as f:
                    f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        return event

    @property
    def events(self) -> list[dict]:
        return list(self._events)

    def items(self) -> dict[str, dict]:
        state: dict[str, dict] = {}
        for e in self._events:
            if e["type"] == "add":
                state[e["item"]["id"]] = copy.deepcopy(e["item"])
            elif e["type"] == "update" and e["id"] in state:
                state[e["id"]].update(copy.deepcopy(e["fields"]))
        return state

    def next_id(self, prefix: str) -> str:
        n = sum(1 for e in self._events if e["type"] == "add") + 1
        return f"{prefix}-{n:04d}"

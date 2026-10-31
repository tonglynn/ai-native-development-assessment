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
import hashlib
import hmac
import json
import threading
import time
from pathlib import Path

GENESIS = "genesis"


class TamperedLog(Exception):
    """The event log failed its integrity check; it is not loaded (fail closed)."""


def _canonical(event: dict) -> bytes:
    return json.dumps({k: v for k, v in event.items() if k != "mac"}, sort_keys=True, ensure_ascii=False, default=str).encode()


def seal(event: dict, prev: str, key: bytes | None) -> dict:
    """Tamper evidence (optional, D42): link the event to the previous one and authenticate it.
    Without a key the link is a plain SHA-256 chain, which anyone who can write the file can recompute."""
    event = dict(event, prev=prev)
    data = _canonical(event)
    event["mac"] = hmac.new(key, data, hashlib.sha256).hexdigest() if key else hashlib.sha256(data).hexdigest()
    return event


def verify_events(events: list[dict], key: bytes | None = None, head: str | None = None) -> dict:
    """Check sequence, links and authentication; with `head` (the last mac, kept elsewhere) also truncation."""
    prev = GENESIS
    for n, e in enumerate(events, 1):
        if e.get("seq") != n:
            return {"ok": False, "seq": e.get("seq"), "reason": f"sequence broken at position {n}"}
        if e.get("prev") != prev:
            return {"ok": False, "seq": n, "reason": "link to the previous event broken"}
        data = _canonical(e)
        want = hmac.new(key, data, hashlib.sha256).hexdigest() if key else hashlib.sha256(data).hexdigest()
        if not hmac.compare_digest(str(e.get("mac")), want):
            return {"ok": False, "seq": n, "reason": "event content does not match its authentication code"}
        prev = e["mac"]
    if head is not None and prev != head:
        return {"ok": False, "seq": len(events), "reason": "log does not end at the anchored head (truncated or extended)"}
    return {"ok": True, "seq": None, "reason": "", "head": prev}


def checkpoint(store: "EventStore", path: Path) -> dict:
    """Write the current head (seq, mac) to a separate append-only checkpoint file (D42 hardening).

    The checkpoint file is the independent trust anchor: kept where whoever can write the log cannot
    (another repository, a signed commit, object storage with retention)."""
    cp = {"seq": len(store.events), "mac": store.head, "ts": round(time.time(), 3)}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(cp) + "\n")
    return cp


def verify_checkpoints(events: list[dict], path: Path, key: bytes | None = None) -> dict:
    """The log must verify, and every checkpoint must still be in it at its position: the log may have
    grown since, but nothing up to a checkpoint was rewritten, removed or cut off."""
    check = verify_events(events, key)
    if not check["ok"]:
        return check
    for line in path.read_text().splitlines():
        cp = json.loads(line)
        if cp["seq"] > len(events) or (cp["seq"] and events[cp["seq"] - 1].get("mac") != cp["mac"]):
            return {"ok": False, "seq": cp["seq"], "reason": f"checkpoint at event {cp['seq']} no longer matches the log"}
    return {"ok": True, "seq": None, "reason": ""}


class EventStore:
    def __init__(self, path: Path | None, *, seal_key: bytes | None = None, sealed: bool = False, head: str | None = None):
        """sealed (D42, opt-in): every new event is chained and authenticated (HMAC with seal_key, or
        SHA-256 without one); an existing sealed log is verified on load and refused if it fails."""
        self.path = path
        self._lock = threading.Lock()
        self._events: list[dict] = []
        self.sealed, self._key = sealed or seal_key is not None, seal_key
        if path and path.exists():
            self._events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            if self.sealed:
                check = verify_events(self._events, self._key, head)
                if not check["ok"]:
                    raise TamperedLog(f"{path}: {check['reason']} (event {check['seq']})")

    @property
    def head(self) -> str:
        return self._events[-1].get("mac", GENESIS) if self._events else GENESIS

    def append(self, event_type: str, **payload) -> dict:
        with self._lock:
            event = {"seq": len(self._events) + 1, "ts": round(time.time(), 3), "type": event_type, **payload}
            if self.sealed:
                event = seal(event, self.head, self._key)
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

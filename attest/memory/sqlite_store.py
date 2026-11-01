"""SQLite backend for the memory event log, for memory shared by several agents or people.

Same interface and semantics as ``EventStore`` (append / events / items / next_id),
so every memory system works on either backend unchanged. Two differences matter
in practice:

* The log lives in one database file that several processes can use at once
  (WAL mode; every append is one transaction), for example several MCP clients
  sharing one team memory. The JSONL store assumes a single writer.
* Besides the append-only ``events`` table, the database keeps the current state
  of every item in an ``items`` table, updated in the same transaction as the
  event. Reading the state is a query, not a replay of the whole log, and the
  state can be inspected with any SQLite tool:

      sqlite3 memory.db "select id, status, json_extract(item, '$.content') from items"

The events table is still the source of truth: ``rebuild_items()`` recomputes
the items table from it, and ``import_jsonl`` / ``export_jsonl`` convert between
the two backends without loss.
"""

from __future__ import annotations

import copy
import json
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      REAL NOT NULL,
    type    TEXT NOT NULL CHECK (type IN ('add', 'update', 'reject')),
    payload TEXT NOT NULL              -- the event without seq/ts/type, as JSON
);
CREATE TABLE IF NOT EXISTS items (
    id       TEXT PRIMARY KEY,
    status   TEXT,
    repo     TEXT,
    item     TEXT NOT NULL,            -- current state of the item, as JSON
    last_seq INTEGER NOT NULL REFERENCES events(seq)
);
CREATE INDEX IF NOT EXISTS items_status_repo ON items (status, repo);
CREATE INDEX IF NOT EXISTS events_type ON events (type);
"""


def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


class SqliteEventStore:
    def __init__(self, path: Path | str | None):
        self.path = Path(path) if path not in (None, ":memory:") else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None: we issue BEGIN IMMEDIATE ourselves, so an append
        # (read seq + write event + write item) is atomic across processes.
        self._db = sqlite3.connect(str(self.path) if self.path else ":memory:", timeout=30,
                                   isolation_level=None, check_same_thread=False)
        self._db.execute("PRAGMA busy_timeout = 30000")
        if self.path:
            self._db.execute("PRAGMA journal_mode = WAL")
        self._db.executescript(SCHEMA)

    # ------------------------------------------------------------------ writes
    def append(self, event_type: str, **payload) -> dict:
        ts = round(time.time(), 3)
        db = self._db
        db.execute("BEGIN IMMEDIATE")
        try:
            cur = db.execute("INSERT INTO events (ts, type, payload) VALUES (?, ?, ?)", (ts, event_type, _dumps(payload)))
            seq = cur.lastrowid
            self._apply(event_type, payload, seq)
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
        return {"seq": seq, "ts": ts, "type": event_type, **json.loads(_dumps(payload))}

    def _apply(self, event_type: str, payload: dict, seq: int) -> None:
        if event_type == "add":
            item = json.loads(_dumps(payload["item"]))
            # A duplicate id (two writers raced between next_id and append) fails
            # loudly instead of silently overwriting the other writer's item.
            self._db.execute("INSERT INTO items (id, status, repo, item, last_seq) VALUES (?, ?, ?, ?, ?)",
                             (item["id"], item.get("status"), item.get("repo"), _dumps(item), seq))
        elif event_type == "update":
            row = self._db.execute("SELECT item FROM items WHERE id = ?", (payload["id"],)).fetchone()
            if row is None:  # same as the JSONL store: updates of unknown items are ignored
                return
            item = json.loads(row[0])
            item.update(json.loads(_dumps(payload["fields"])))
            self._db.execute("UPDATE items SET status = ?, repo = ?, item = ?, last_seq = ? WHERE id = ?",
                             (item.get("status"), item.get("repo"), _dumps(item), seq, payload["id"]))

    # ------------------------------------------------------------------- reads
    @property
    def events(self) -> list[dict]:
        rows = self._db.execute("SELECT seq, ts, type, payload FROM events ORDER BY seq").fetchall()
        return [{"seq": s, "ts": ts, "type": t, **json.loads(p)} for s, ts, t, p in rows]

    def items(self) -> dict[str, dict]:
        rows = self._db.execute("SELECT id, item FROM items ORDER BY last_seq IS NULL, rowid").fetchall()
        return {i: json.loads(it) for i, it in rows}

    def next_id(self, prefix: str) -> str:
        n = self._db.execute("SELECT COUNT(*) FROM events WHERE type = 'add'").fetchone()[0] + 1
        return f"{prefix}-{n:04d}"

    # --------------------------------------------------------------- utilities
    def rebuild_items(self) -> None:
        """Recompute the items table from the event log (the log is the source of truth)."""
        db = self._db
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute("DELETE FROM items")
            for seq, t, p in db.execute("SELECT seq, type, payload FROM events ORDER BY seq").fetchall():
                self._apply(t, json.loads(p), seq)
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise

    def import_jsonl(self, path: Path) -> int:
        """Append every event of a JSONL log (keeping its order and timestamps). Returns the count."""
        n = 0
        db = self._db
        db.execute("BEGIN IMMEDIATE")
        try:
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                e = json.loads(line)
                payload = {k: v for k, v in e.items() if k not in ("seq", "ts", "type")}
                cur = db.execute("INSERT INTO events (ts, type, payload) VALUES (?, ?, ?)", (e["ts"], e["type"], _dumps(payload)))
                self._apply(e["type"], payload, cur.lastrowid)
                n += 1
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
        return n

    def export_jsonl(self, path: Path) -> int:
        events = self.events
        Path(path).write_text("".join(_dumps(e) + "\n" for e in events), encoding="utf-8")
        return len(events)

    def close(self) -> None:
        self._db.close()


def open_store(store_dir: Path | None, backend: str | None = None):
    """The event store for a memory directory.

    ``backend`` is "jsonl" (default; ``events.jsonl``, used by the experiments so
    the memory is committed with the results) or "sqlite" (``memory.db``). The
    ATTEST_STORE environment variable sets the default.
    """
    import os

    from .store import EventStore

    backend = (backend or os.environ.get("ATTEST_STORE") or "jsonl").lower()
    if backend == "sqlite":
        return SqliteEventStore(store_dir / "memory.db" if store_dir else None)
    if backend == "jsonl":
        return EventStore(store_dir / "events.jsonl" if store_dir else None)
    raise ValueError(f"unknown store backend {backend!r} (use 'jsonl' or 'sqlite')")

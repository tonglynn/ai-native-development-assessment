"""The SQLite backend behaves exactly like the JSONL event log, and is safe for several writers."""

import multiprocessing as mp
import sqlite3
from pathlib import Path

import pytest

from attest.memory import make_memory
from attest.memory.sqlite_store import SqliteEventStore, open_store
from attest.memory.store import EventStore

ROOT = Path(__file__).resolve().parent.parent
REAL_LOGS = sorted(ROOT.glob("runs/*/attest/events.jsonl")) + sorted(ROOT.glob("runs/*/ace/events.jsonl"))


def _ops(store):
    a = store.append("add", item={"id": store.next_id("at"), "status": "active", "repo": "ledgerly", "content": "use round_money", "uses": 0})
    store.append("add", item={"id": store.next_id("at"), "status": "active", "repo": "simkit", "content": "floats only"})
    store.append("update", id=a["item"]["id"], fields={"uses": 1}, reason="shown")
    store.append("update", id=a["item"]["id"], fields={"status": "suspect"}, reason="blamed")
    store.append("update", id="at-9999", fields={"status": "retired"}, reason="unknown id is ignored")
    store.append("reject", task_id="E01", candidate={"content": "x"}, reason="no evidence")


def test_same_state_and_events_as_jsonl(tmp_path):
    j, s = EventStore(tmp_path / "events.jsonl"), SqliteEventStore(tmp_path / "memory.db")
    _ops(j)
    _ops(s)
    assert s.items() == j.items()
    strip = lambda evs: [{k: v for k, v in e.items() if k != "ts"} for e in evs]  # noqa: E731
    assert strip(s.events) == strip(j.events)
    assert s.next_id("at") == j.next_id("at") == "at-0003"


def test_persists_across_connections(tmp_path):
    s = SqliteEventStore(tmp_path / "memory.db")
    _ops(s)
    before = s.items()
    s.close()
    assert SqliteEventStore(tmp_path / "memory.db").items() == before


def test_items_table_can_be_rebuilt_from_the_log(tmp_path):
    s = SqliteEventStore(tmp_path / "memory.db")
    _ops(s)
    before = s.items()
    s._db.execute("UPDATE items SET item = '{}'")  # corrupt the derived table
    s.rebuild_items()
    assert s.items() == before


def test_duplicate_item_id_fails_loudly(tmp_path):
    s = SqliteEventStore(tmp_path / "memory.db")
    s.append("add", item={"id": "at-0001", "status": "active"})
    with pytest.raises(sqlite3.IntegrityError):
        s.append("add", item={"id": "at-0001", "status": "active"})
    assert len(s.events) == 1  # the failed append left nothing behind


@pytest.mark.skipif(not REAL_LOGS, reason="no committed memory logs")
@pytest.mark.parametrize("log", REAL_LOGS[:4], ids=lambda p: "/".join(p.parts[-3:-1]))
def test_real_logs_import_and_export_without_loss(tmp_path, log):
    s = SqliteEventStore(tmp_path / "memory.db")
    assert s.import_jsonl(log) == len(EventStore(log).events)
    assert s.items() == EventStore(log).items()
    s.export_jsonl(tmp_path / "back.jsonl")
    assert EventStore(tmp_path / "back.jsonl").items() == EventStore(log).items()


def _writer(path, worker, n):
    s = SqliteEventStore(path)
    for k in range(n):
        s.append("add", item={"id": f"w{worker}-{k}", "status": "active"})
        s.append("update", id=f"w{worker}-{k}", fields={"uses": k}, reason="concurrent")


def test_several_processes_can_write_at_once(tmp_path):
    path = tmp_path / "shared" / "memory.db"
    SqliteEventStore(path).close()
    procs = [mp.get_context("spawn").Process(target=_writer, args=(path, w, 40)) for w in range(4)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(60)
        assert p.exitcode == 0
    s = SqliteEventStore(path)
    seqs = [e["seq"] for e in s.events]
    assert seqs == list(range(1, 4 * 40 * 2 + 1))  # nothing lost, no duplicate sequence numbers
    items = s.items()
    assert len(items) == 160 and all(items[f"w{w}-{k}"]["uses"] == k for w in range(4) for k in range(40))


def test_backend_selection(tmp_path, monkeypatch):
    monkeypatch.delenv("ATTEST_STORE", raising=False)
    assert isinstance(open_store(tmp_path / "a"), EventStore)
    assert isinstance(open_store(tmp_path / "b", "sqlite"), SqliteEventStore)
    monkeypatch.setenv("ATTEST_STORE", "sqlite")
    for condition in ("attest", "reasoningbank", "ace"):
        memory = make_memory(condition, tmp_path / condition)
        assert isinstance(memory.store, SqliteEventStore)
        assert (tmp_path / condition / "memory.db").exists()
    with pytest.raises(ValueError):
        open_store(tmp_path / "c", "postgres")

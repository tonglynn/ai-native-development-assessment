"""In-process audit trail. Production ships these entries to the ledger service."""

from .clock import utcnow

_EVENTS: list[dict] = []


def record(event: str, **fields) -> dict:
    entry = {"event": event, "at": utcnow(), **fields}
    _EVENTS.append(entry)
    return entry


def events(event: str | None = None) -> list[dict]:
    return [e for e in _EVENTS if event is None or e["event"] == event]


def clear() -> None:
    _EVENTS.clear()

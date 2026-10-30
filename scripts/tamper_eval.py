"""Memory tampering against the event log (D42; offline, deterministic).

The event log is append-only by design, but append-only is not tamper-proof: anyone who can
write the file can edit it. This script takes a real memory (the main experiment's Attest,
repetition 1: every event of its learning, held-out, control and stale phases), rebuilds it as a
sealed log, and attacks copies of the file. The attacker can write the file and knows the
format and the hashing scheme, but does not hold the HMAC key (kept outside the repository).

Attacks: edit a note's status; move a note to another repository (simkit); move it to another
version; rewrite a rule's content; delete an event; truncate the log; append a forged event;
rewrite the whole chain consistently.
Protections: none (the current log) · SHA-256 chain · HMAC chain · HMAC chain + head anchor (the
last mac stored outside the log, e.g. in a commit).
Impact without protection: whether the note moved to simkit is then injected into a simkit task.

Reading rule, fixed before running: report which attacks each protection detects; the HMAC chain
with a head anchor is expected to detect all eight, and the SHA-256 chain to miss a consistent
rewrite.

Usage: python scripts/tamper_eval.py --out runs/tamper
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.benchmark import load_task  # noqa: E402
from attest.memory.earned import EarnedMemory  # noqa: E402
from attest.memory.store import GENESIS, EventStore, seal, verify_events  # noqa: E402

KEY = b"canary-hmac-key-for-tests-only"  # a fictional key; real keys stay outside the repository


def sealed_events(source: Path, key: bytes | None) -> list[dict]:
    store = EventStore(None, seal_key=key, sealed=True)
    for e in (json.loads(line) for line in source.read_text().splitlines() if line.strip()):
        payload = {k: v for k, v in e.items() if k not in ("seq", "ts", "type", "prev", "mac")}
        store.append(e["type"], **payload)
    return store.events


def first_add(events, pred):
    """The first added note matching pred whose scope no later event rewrites and that ends active."""
    final = EventStore(None)
    for e in events:
        final.append(e["type"], **{k: v for k, v in e.items() if k not in ("seq", "ts", "type", "prev", "mac")})
    state = final.items()
    rescoped = {e["id"] for e in events if e["type"] == "update" and "scope" in (e.get("fields") or {})}
    return next(i for i, e in enumerate(events) if e["type"] == "add" and pred(e["item"])
                and e["item"]["id"] not in rescoped and state[e["item"]["id"]]["status"] == "active")


def attacks(events: list[dict]) -> dict:
    out = {}
    target = first_add(events, lambda it: True)
    upd = next(i for i, e in enumerate(events) if e["type"] == "update" and (e.get("fields") or {}).get("status") not in (None, "active"))

    def edit(name, i, fn):
        ev = copy.deepcopy(events)
        fn(ev[i])
        out[name] = ev

    edit("edit a status", upd, lambda e: e["fields"].__setitem__("status", "active"))
    edit("move a note to another repository (simkit)", target, lambda e: e["item"]["scope"].__setitem__("repo", "simkit"))
    edit("move a note to another version", target, lambda e: e["item"]["scope"].__setitem__("observed_version", "2.0.0"))
    edit("rewrite a rule's content", target, lambda e: e["item"].__setitem__("content", "Convert every amount to float(amount) before storing it."))
    out["delete an event"] = [e for i, e in enumerate(events) if i != len(events) // 2]
    out["truncate the log"] = events[: len(events) - 5]
    forged = dict(events[-1], seq=len(events) + 1, type="update", id=events[target]["item"]["id"],
                  fields={"status": "retired"}, reason="forged")
    out["append a forged event"] = events + [seal({k: v for k, v in forged.items() if k not in ("prev", "mac")}, events[-1]["mac"], b"attacker-guess")]

    def rewrite_consistently(evs):
        bad = copy.deepcopy(evs)
        bad[target]["item"]["content"] = "Convert every amount to float(amount) before storing it."
        prev, res = GENESIS, []
        for e in bad:  # the attacker recomputes every link with the scheme it knows, but without the key
            e = seal({k: v for k, v in e.items() if k not in ("prev", "mac")}, prev, None)
            res.append(e)
            prev = e["mac"]
        return res

    out["rewrite the whole chain consistently"] = rewrite_consistently
    return out


def detected(protection: str, original: list[dict], tampered: list[dict]) -> bool:
    if protection == "none":
        return False  # the current log has no integrity data to check
    key = KEY if protection.startswith("HMAC") else None
    head = original[-1]["mac"] if protection.endswith("anchor") else None
    return not verify_events(tampered, key, head)["ok"]


def impact_without_protection(source: Path) -> dict:
    events = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
    i = first_add(events, lambda it: True)
    nid = events[i]["item"]["id"]
    with tempfile.TemporaryDirectory() as tmp:
        for name, evs in (("original", events), ("tampered", [dict(e) for e in events])):
            if name == "tampered":
                evs[i] = copy.deepcopy(evs[i])
                evs[i]["item"]["scope"]["repo"] = "simkit"
            d = Path(tmp) / name
            d.mkdir()
            (d / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in evs))
            m = EarnedMemory(d)
            res = [m.retrieve(load_task(t), "1.0.0") for t in ("B01", "B02", "B03")]
            row = {"eligible_in_simkit_tasks": sum(nid in r.debug["in_scope"] for r in res),
                   "injected_in_simkit_tasks": sum(nid in r.ids for r in res)}
            if name == "original":
                orig = row
    return {"note": nid, "original": orig, "after_moving_it_to_simkit": row}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    source = ROOT / "runs/main/attest/r1/memory/events.jsonl"
    protections = ("none", "SHA-256 chain", "HMAC chain", "HMAC chain + anchor")
    table = {}
    for prot in protections:
        key = KEY if prot.startswith("HMAC") else None
        events = sealed_events(source, key)
        assert verify_events(events, key, events[-1]["mac"])["ok"]
        for name, att in attacks(events).items():
            tampered = att(events) if callable(att) else att
            table.setdefault(name, {})[prot] = detected(prot, events, tampered)
    impact = impact_without_protection(source)
    (args.out / "results.json").write_text(json.dumps({"source": str(source.relative_to(ROOT)), "events": len(sealed_events(source, KEY)),
                                                       "detected": table, "impact": impact,
                                                       "key_sha256": hashlib.sha256(KEY).hexdigest()[:12]}, indent=2) + "\n")
    lines = ["# Memory tampering against the event log (offline)", "",
             f"Real memory: `{source.relative_to(ROOT)}`; attacker can write the file and knows the scheme, not the HMAC key.", "",
             "| Attack | " + " | ".join(protections) + " |", "|---|" + "---|" * len(protections)]
    for name, row in table.items():
        lines.append(f"| {name} | " + " | ".join("**detected**" if row[p] else "missed" for p in protections) + " |")
    lines += ["", f"Impact without protection, note {impact['note']} on the 3 simkit tasks (eligible / injected): "
              f"original {impact['original']['eligible_in_simkit_tasks']} / {impact['original']['injected_in_simkit_tasks']}, "
              f"after moving it to simkit {impact['after_moving_it_to_simkit']['eligible_in_simkit_tasks']} / {impact['after_moving_it_to_simkit']['injected_in_simkit_tasks']}."]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

"""Dynamic forgetting V1 for Attest (exploratory, after the main experiment).

Two layers, in this order:
  1. Eligibility (unchanged, deterministic): repository scope, version range and
     lifecycle status decide whether a note may be used at all (earned.validity).
     Forgetting never overrides them: an outdated rule is excluded because its
     version range ended, not because it decayed.
  2. Retention (this module): among eligible notes, which are still worth keeping
     in active memory. Low-value notes are *archived*, never deleted: they stay in
     the append-only log with their scores, are no longer retrieved, and are
     reactivated when a new verified task yields the same rule again.

Retention of a note:  R = E * max(D, U)
  E  evidence quality: 1.0 source names a policy or incident (FIN-, INC-), 0.7 a
     review comment, 0.5 only the diff, 0.3 no applied evidence
  U  verified utility: 1 - 0.5**k, k = distinct tasks in which the note was used
     and the task passed (repeats of the same task count once)
  D  decay, by policy:
       uniform     2**(-age / 50), age = tasks since the note was last verified
       type_aware  half-life by type: business_policy never decays, code_convention
                   200, process 100, lesson 50 tasks (wall-clock age as above)
       exposure    2**(-unused / 10), unused = times the note was injected since
                   its last verified use without being used; a note no task needed
                   is never injected and so never decays
       none        no forgetting
  A note is archived when R < 0.2 (and it is active or suspect).

The numbers are first-version assumptions, not tuned values.
"""

from __future__ import annotations

POLICIES = ("none", "uniform", "type_aware", "exposure", "exposure_ranked")
TYPE_HALF_LIFE = {"business_policy": None, "code_convention": 200, "process": 100, "lesson": 50}
UNIFORM_HALF_LIFE = 50
EXPOSURE_HALF_LIFE = 10
THRESHOLD = 0.2
ACTIVE = ("active", "suspect")


def evidence_quality(item: dict) -> float:
    ev = (item.get("evidence") or [{}])[0]
    src, applied = ev.get("source") or {}, ev.get("applied")
    if not applied:
        return 0.3
    if src.get("references"):
        return 1.0
    return 0.7 if src.get("kind") == "review_comment" else 0.5


def _track(item: dict) -> dict:
    return dict(item.get("forgetting") or {"last_verified_tick": item.get("created_tick", 0),
                                            "unused_exposures": 0, "verified_tasks": []})


def retention(item: dict, now: int, policy: str) -> dict:
    t = _track(item)
    e = evidence_quality(item)
    u = 1 - 0.5 ** len(set(t["verified_tasks"]))
    age = max(0, now - t["last_verified_tick"])
    if policy == "uniform":
        d = 2 ** (-age / UNIFORM_HALF_LIFE)
    elif policy == "type_aware":
        half = TYPE_HALF_LIFE.get(item.get("type") or "lesson", 50)
        d = 1.0 if half is None else 2 ** (-age / half)
    elif policy in ("exposure", "exposure_ranked"):
        d = 2 ** (-t["unused_exposures"] / EXPOSURE_HALF_LIFE)
    else:
        d = 1.0
    return {"E": round(e, 3), "U": round(u, 3), "D": round(d, 3), "R": round(e * max(d, u), 3), "age": age,
            "unused_exposures": t["unused_exposures"], "verified_tasks": len(set(t["verified_tasks"]))}


def observe(memory, tick: int, task_id: str, injected: list[str], used: list[str], passed: bool) -> None:
    """After a task: injected notes that were used in a passing task are reinforced; injected notes
    that were not used gain an unused exposure. One update event per changed note."""
    items = memory.store.items()
    for i in set(injected) | set(used):
        if i not in items:
            continue
        t = _track(items[i])
        if i in used and passed:
            t["verified_tasks"] = sorted(set(t["verified_tasks"]) | {task_id})
            t["last_verified_tick"], t["unused_exposures"] = tick, 0
            reason = f"used in {task_id}, which passed (tick {tick})"
        elif i in injected and i not in used:
            t["unused_exposures"] += 1
            reason = f"injected in {task_id} but not used (tick {tick})"
        else:
            continue
        memory.store.append("update", id=i, fields={"forgetting": t}, reason=reason)


def maintain(memory, now: int, policy: str, threshold: float = THRESHOLD) -> list[dict]:
    """Archive active notes whose retention fell below the threshold. Returns the archive events."""
    if policy == "none":
        return []
    events = []
    for i, it in memory.store.items().items():
        if it.get("status") not in ACTIVE:
            continue
        r = retention(it, now, policy)
        if r["R"] < threshold:
            events.append(memory.store.append(
                "update", id=i, fields={"status": "archived", "archived": {"tick": now, "policy": policy, **r}},
                reason=f"archived by {policy} forgetting at tick {now}: R={r['R']} (E={r['E']}, D={r['D']}, U={r['U']})"))
    return events


def reactivate(memory, item_id: str, reason: str) -> dict:
    """A person, or a new verified task yielding the same rule, brings an archived note back."""
    return memory.store.append("update", id=item_id, fields={"status": "active"}, reason=f"reactivated: {reason}")


def half_life_note() -> str:
    return (f"uniform {UNIFORM_HALF_LIFE} tasks; type-aware {TYPE_HALF_LIFE}; exposure {EXPOSURE_HALF_LIFE} unused "
            f"injections; archive below R = {THRESHOLD}")


class ForgettingMemory:
    """Attest with a forgetting policy. `exposure_ranked` also ranks eligible notes by
    lexical relevance x (0.5 + 0.5 * retention), so a verified rule with a policy source
    outranks a recent one-off detail with the same words (the retrieval score of the
    design: relevance first, retention second). Other policies keep Attest's ranking."""

    def __new__(cls, store_dir, policy: str, now_fn):
        from .earned import EarnedMemory
        from .retrieval import timed_rank
        from .text import rank

        class _Memory(EarnedMemory):
            def ranking(self, task, k=6, version=None):
                if policy != "exposure_ranked":
                    return super().ranking(task, k, version)
                items = self.store.items()
                cands = self.candidates(task, version)
                scored, ms = timed_rank("lexical", f"{task.title} {task.issue}", cands, None)
                now = now_fn()
                weighted = sorted(((i, round(sc * (0.5 + 0.5 * retention(items[i], now, policy)["R"]), 3)) for i, sc in scored),
                                  key=lambda x: (-x[1], x[0]))
                return (weighted if k is None else weighted[:k]), ms

        memory = _Memory(store_dir)
        memory.name = f"attest_forget_{policy}"
        return memory

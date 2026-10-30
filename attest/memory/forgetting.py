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

V1.1 (opt-in through `params` and `observe(verified=...)`; V1 stays the default):
  - V1 lets one verified use protect a note for ever (U >= 0.5, so R >= 0.25 > 0.2).
    With utility_factor, U also decays, that many times slower than D.
  - A note's progress is recorded in stages: injected, adopted (used), behaviour
    verified. Only verified use reinforces; "the task passed" alone does not.
  - protect_cited: a note citing a policy or incident (FIN-, POL-, SEC-, INC-) never decays,
    whatever its type label. Added to the type protection (business_policy never decays
    under type_aware), not a replacement for it.
  - utility_factor = 4 is an experimental setting; 2 and 8 are reported beside it.
  - Fix, for V1 too: reactivation resets the decay clock, so a note restored by new
    evidence is not archived again at the next maintenance. (No published run reactivated
    a note: the streams never re-learn, and end-to-end runs do not update memory.)
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
    from . import admission

    if not applied:
        return 0.3
    if any(r.split("-", 1)[0] in admission.POLICY_PREFIXES for r in src.get("references") or []):
        return 1.0
    return 0.7 if src.get("kind") == "review_comment" else 0.5


def _track(item: dict) -> dict:
    return dict(item.get("forgetting") or {"last_verified_tick": item.get("created_tick", 0),
                                            "unused_exposures": 0, "verified_tasks": []})


def retention(item: dict, now: int, policy: str, params: dict | None = None) -> dict:
    """params: half_life (uniform), type_scale (type_aware: multiplies every finite type half-life),
    exposure_half_life (sensitivity analysis); utility_factor (V1.1): if set, historical utility U
    also decays, `utility_factor` times slower than D, so a note used once is not kept forever;
    policy rules (no finite half-life) keep their utility. protect_cited (V1.1): a note whose
    evidence cites a policy or incident (admission.POLICY_PREFIXES) never decays either, whatever
    type the distiller gave it (it typed the same idempotency rule `process` in two repetitions
    and `business_policy` in the third). This is added to the type protection, not a
    replacement: under type_aware a note typed business_policy still never decays, cited or
    not. The utility_factor value (4) is an experimental setting, not a tuned optimum.
    Defaults are V1, fixed before any run."""
    from . import admission

    params = params or {}
    t = _track(item)
    e = evidence_quality(item)
    k = len(set(t["verified_tasks"]) | set(t.get("demand_tasks") or []))  # demand: V2, empty otherwise
    u = 1 - 0.5 ** k
    age = max(0, now - t["last_verified_tick"])
    clock, half = age, None  # the quantity D decays over, and its half-life
    if policy == "uniform":
        half = params.get("half_life", UNIFORM_HALF_LIFE)
    elif policy == "type_aware":
        half = TYPE_HALF_LIFE.get(item.get("type") or "lesson", 50)
        half = None if half is None else half * params.get("type_scale", 1.0)
    elif policy in ("exposure", "exposure_ranked"):
        clock, half = t["unused_exposures"], params.get("exposure_half_life", EXPOSURE_HALF_LIFE)
    if params.get("protect_cited") and admission.policy_references(item):
        half = None
    if params.get("stability") and half is not None:
        # V2: no utility floor. Each independent verified (or demanded) task multiplies the
        # half-life by `stability`, as in spaced repetition: a detail verified once still fades.
        half = half * params["stability"] ** k
        d = 2 ** (-clock / half)
        return {"E": round(e, 3), "U": round(u, 3), "D": round(d, 3), "R": round(e * d, 3), "age": age,
                "unused_exposures": t["unused_exposures"], "verified_tasks": k, "half_life": half}
    d = 1.0 if half is None else 2 ** (-clock / half)
    if params.get("utility_factor") and half is not None:
        u *= 2 ** (-clock / (half * params["utility_factor"]))
    return {"E": round(e, 3), "U": round(u, 3), "D": round(d, 3), "R": round(e * max(d, u), 3), "age": age,
            "unused_exposures": t["unused_exposures"], "verified_tasks": k}


def observe(memory, tick: int, task_id: str, injected: list[str], used: list[str], passed: bool,
            verified: list[str] | None = None, *, negative=(), demand=(), relevant=None) -> None:
    """After a task, record how far each note got: retrieved, injected, adopted (used), verified.

    V1 (verified=None): a note used in a passing task is reinforced.
    V1.1 (verified given): only notes whose related behaviour was checked and passed (e.g. the
    hidden test of the note's convention) are reinforced; a note adopted in a passing task whose
    behaviour nobody checked is counted as adopted but not reinforced ("the task passed" is not
    "this note contributed"). Injected notes that were not used gain an unused exposure.

    V2, each optional and empty by default (V1 and V1.1 behave as before):
      negative  notes adopted in this task whose related check then failed: negative evidence
      demand    notes about a convention this task needed and failed without (the review or the
                test named it): positive evidence although they were not injected; an archived
                or dormant note is reactivated, with its clock reset
      relevant  if given, an injected but unused note gains an unused exposure only when it is
                in this list (the task touches the note's files), not for every injection"""
    items = memory.store.items()
    reinforce = set(used) if verified is None else set(verified)
    for i in set(injected) | set(used) | reinforce | set(negative) | set(demand):
        if i not in items:
            continue
        it, fields = items[i], {}
        t = _track(it)
        if i in negative:
            t["negative"] = t.get("negative", 0) + 1
            reason = f"adopted in {task_id}, and its check failed (tick {tick})"
        elif i in demand:
            if it.get("status") in ("retired", "superseded") or t.get("negative", 0) > 0:
                # eligibility first: demand never revives a retracted or replaced rule, nor one
                # whose check failed after it was followed (negative evidence outranks demand)
                continue
            t["demand_tasks"] = sorted(set(t.get("demand_tasks") or []) | {task_id})
            t["last_verified_tick"], t["unused_exposures"] = tick, 0
            reason = f"needed in {task_id}: its convention failed without it (tick {tick})"
            if it.get("status") in ("archived", "dormant"):
                fields["status"] = "active"
                reason += "; reactivated"
        elif i in used and i not in reinforce:
            t["adopted_unverified"] = t.get("adopted_unverified", 0) + 1
            reason = f"adopted in {task_id}, behaviour not verified (tick {tick})"
        elif i in reinforce and passed:
            t["verified_tasks"] = sorted(set(t["verified_tasks"]) | {task_id})
            t["last_verified_tick"], t["unused_exposures"] = tick, 0
            reason = f"used in {task_id}, which passed (tick {tick})"
            if it.get("status") == "dormant":
                fields["status"] = "active"
                reason += "; woken from dormant"
        elif i in injected and i not in used:
            if relevant is not None and i not in relevant:
                continue
            t["unused_exposures"] += 1
            reason = f"injected in {task_id} but not used (tick {tick})"
        else:
            continue
        fields["forgetting"] = t
        memory.store.append("update", id=i, fields=fields, reason=reason)


def maintain(memory, now: int, policy: str, threshold: float = THRESHOLD, params: dict | None = None) -> list[dict]:
    """Archive active notes whose retention fell below the threshold. Returns the archive events.

    V2 (params["dormant"]): three evidence states. A note with negative evidence is archived; a
    note whose retention fell below the threshold without negative evidence becomes *dormant*
    (still injected where it was learned, woken by verified use or demand), because "no one
    used it lately" is not "it is wrong"."""
    if policy == "none":
        return []
    events = []
    for i, it in memory.store.items().items():
        if (params or {}).get("dormant"):
            if it.get("status") in (*ACTIVE, "dormant") and _track(it).get("negative", 0) > 0:
                events.append(memory.store.append("update", id=i, fields={"status": "archived", "archived": {"tick": now, "why": "negative evidence"}},
                                                  reason=f"archived at tick {now}: its check failed after it was adopted"))
                continue
            if it.get("status") not in ACTIVE:
                continue
            r = retention(it, now, policy, params)
            if r["R"] < threshold:
                events.append(memory.store.append("update", id=i, fields={"status": "dormant", "dormant": {"tick": now, **r}},
                                                  reason=f"dormant at tick {now}: R={r['R']}, no negative evidence"))
            continue
        if it.get("status") not in ACTIVE:
            continue
        r = retention(it, now, policy, params)
        if r["R"] < threshold:
            events.append(memory.store.append(
                "update", id=i, fields={"status": "archived", "archived": {"tick": now, "policy": policy, **r}},
                reason=f"archived by {policy} forgetting at tick {now}: R={r['R']} (E={r['E']}, D={r['D']}, U={r['U']})"))
    return events


def reset_track(item: dict, now: int, task_id: str | None = None) -> dict:
    """The forgetting state after reactivation: verified now, no unused exposures. Without this a
    reactivated note keeps its old age and is archived again at the next maintenance."""
    t = _track(item)
    t["last_verified_tick"], t["unused_exposures"] = now, 0
    if task_id:
        t["verified_tasks"] = sorted(set(t["verified_tasks"]) | {task_id})
    return t


def reactivate(memory, item_id: str, reason: str, now: int, task_id: str | None = None) -> dict:
    """A person, or a new verified task yielding the same rule, brings an archived note back.

    `now` (the current task clock) is required: reactivation always resets the decay clock,
    otherwise the note keeps its old age and is archived again at the next maintenance."""
    if not isinstance(now, int):
        raise TypeError("reactivate needs the current task clock `now`")
    fields = {"status": "active", "forgetting": reset_track(memory.store.items()[item_id], now, task_id)}
    return memory.store.append("update", id=item_id, fields=fields, reason=f"reactivated: {reason}")


def half_life_note() -> str:
    return (f"uniform {UNIFORM_HALF_LIFE} tasks; type-aware {TYPE_HALF_LIFE}; exposure {EXPOSURE_HALF_LIFE} unused "
            f"injections; archive below R = {THRESHOLD}")


class ForgettingMemory:
    """Attest with a forgetting policy and, optionally, trust-tiered admission (admission.py).

    `exposure_ranked` ranks eligible notes by lexical relevance x (0.5 + 0.5 * retention).
    `tiered=True` excludes candidates outside their files and ranks rules before candidates.
    Other settings keep Attest's ranking."""

    def __new__(cls, store_dir, policy: str, now_fn, tiered: bool = False):
        from . import admission
        from .earned import EarnedMemory
        from .retrieval import timed_rank

        class _Memory(EarnedMemory):
            def _admit(self, task, repo_version, run, cand, changed):
                events = super()._admit(task, repo_version, run, cand, changed)
                for e in list(events):  # a verified task confirmed an archived note: restart its clock
                    if e["type"] == "update" and "reactivated from the archive" in e.get("reason", ""):
                        t = reset_track(self.store.items()[e["id"]], now_fn(), task.id)
                        events.append(self.store.append("update", id=e["id"], fields={"forgetting": t},
                                                        reason=f"forgetting clock reset on reactivation (tick {now_fn()})"))
                return events

            def _exclusion(self, item, task, version):
                if item.get("status") == "dormant":  # V2: eligible like an active note, but only in its own files
                    why = super()._exclusion(dict(item, status="active"), task, version)
                    files = set((item.get("scope") or {}).get("files") or [])
                    return why or ("" if files & admission.files_named(task) else "dormant: injected only in its own files")
                why = super()._exclusion(item, task, version)
                if why or not tiered or admission.injectable_here(item, task):
                    return why
                return "candidate: seen once, injected only in its own files"

            def ranking(self, task, k=6, version=None):
                if policy != "exposure_ranked" and not tiered:
                    return super().ranking(task, k, version)
                items = self.store.items()
                scored, ms = timed_rank("lexical", f"{task.title} {task.issue}", self.candidates(task, version), None)
                if policy == "exposure_ranked":
                    now = now_fn()
                    scored = [(i, round(sc * (0.5 + 0.5 * retention(items[i], now, policy)["R"]), 3)) for i, sc in scored]
                if tiered:  # tier first (rules with any relevance, then candidates), relevance within a tier
                    key = lambda x: (0 if x[1] > 0 and admission.tier(items[x[0]]) in admission.RULE_TIERS else 1 if x[1] > 0 else 2, -x[1], x[0])  # noqa: E731
                else:
                    key = lambda x: (-x[1], x[0])  # noqa: E731
                ranked = sorted(scored, key=key)
                return (ranked if k is None else ranked[:k]), ms

        memory = _Memory(store_dir)
        memory.name = f"attest_forget_{policy}" + ("_tiered" if tiered else "")
        return memory

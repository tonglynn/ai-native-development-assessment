"""Context manager: order kept, tool results stay with their calls, budget respected, constraints never lost."""

import json

from attest.context.manager import ContextManager, ManagedModel, extract_state, fidelity, tokens_of

RULE = ('[team convention] Support-initiated refunds above the approval threshold need a second approver: accept an '
        'optional keyword-only `approved_by=None`. The threshold is 500.00 before 2.0.0, 1000.00 since 2.0.0 (FIN-2026-09).')


def step(i, output="x" * 800):
    call = {"id": f"c{i}", "type": "function", "function": {"name": "bash", "arguments": json.dumps({"command": f"cat file{i}.py"})}}
    return [{"role": "assistant", "content": "", "tool_calls": [call]},
            {"role": "tool", "tool_call_id": f"c{i}", "content": json.dumps({"returncode": 0, "output": output})}]


def session():
    msgs = [{"role": "system", "content": "system prompt"}, {"role": "user", "content": "earlier task"}]
    msgs += step(0) + [{"role": "user", "content": "Review comments:\n" + RULE}]
    for i in range(1, 30):
        msgs += step(i)
    msgs.append({"role": "user", "content": "NEW TASK: outage refunds"})
    return msgs


def test_window_drops_the_rule_manager_keeps_it_verbatim():
    msgs = session()
    task_index = len(msgs) - 1
    window = ContextManager("window", 3000).assemble(msgs, task_index)
    manager = ContextManager("manager", 3000).assemble(msgs, task_index)
    text = lambda ctx: "\n".join(str(m.get("content")) for m in ctx)  # noqa: E731
    assert "approved_by" not in text(window)
    assert "`approved_by=None`" in text(manager) and "1000.00 since 2.0.0" in text(manager)
    for ctx in (window, manager):
        assert tokens_of(ctx) <= 3000
        assert ctx[0]["content"] == "system prompt" and any(m.get("content") == "NEW TASK: outage refunds" for m in ctx)


def test_order_kept_and_tool_results_never_orphaned():
    msgs = session()
    ctx = ContextManager("manager", 3000).assemble(msgs, len(msgs) - 1)
    ids_called = set()
    for m in ctx:
        for c in m.get("tool_calls") or []:
            ids_called.add(c["id"])
        if m["role"] == "tool":
            assert m["tool_call_id"] in ids_called  # its call came earlier in the context
    kept = [msgs.index(m) for m in ctx if m in msgs]
    assert kept == sorted(kept)


def test_under_budget_or_full_is_unchanged():
    msgs = session()[:6]
    assert ContextManager("manager", 100000).assemble(msgs, 1) == msgs
    assert ContextManager("full", 10).assemble(session(), 1) == session()


def test_extraction_and_summary_fidelity():
    state = extract_state(session())
    assert any("approved_by" in s for _, s in state.constraints)
    assert {"1000.00", "approved_by=none", "fin-2026-09"} <= state.pinned_tokens()
    lossy = fidelity("Large support refunds need approval.", state)
    assert "1000.00" in lossy["dropped"] and lossy["kept"] < lossy["pinned"]


def test_managed_model_prepends_session_and_assembles():
    class Inner:
        config = "cfg"

        def __init__(self):
            self.seen = None

        def query(self, messages, **kw):
            self.seen = messages
            return {"role": "assistant", "content": "ok"}

    inner, prefix = Inner(), session()[1:-1]
    model = ManagedModel(inner, ContextManager("manager", 3000), prefix)
    model.query([{"role": "system", "content": "system prompt"}, {"role": "user", "content": "NEW TASK: outage refunds"}])
    assert inner.seen[0]["content"] == "system prompt" and tokens_of(inner.seen) <= 3000
    assert "approved_by" in "\n".join(str(m.get("content")) for m in inner.seen)
    assert model.config == "cfg"  # attributes pass through to the wrapped model


def test_sanitize_removes_unanswered_tool_calls():
    """INC-2: a saved trajectory ends with the submit call, whose result is not a tool message."""
    from attest.context.manager import sanitize

    submit = {"role": "assistant", "content": "", "tool_calls": [{"id": "z", "type": "function",
                                                                   "function": {"name": "bash", "arguments": "{}"}}]}
    msgs = step(1) + [submit, {"role": "user", "content": "next task"}, {"role": "tool", "tool_call_id": "q", "content": "{}"}]
    clean = sanitize(msgs)
    assert clean == step(1) + [{"role": "user", "content": "next task"}]
    for i, m in enumerate(clean):  # every remaining call is answered right after it
        for c in m.get("tool_calls") or []:
            assert any(n.get("tool_call_id") == c["id"] for n in clean[i + 1:])

"""Code citations in semantic review (D50): excerpts are chosen deterministically and checked verbatim."""

from attest.memory import governance


def test_code_citation_is_checked(monkeypatch):
    cand = {"title": "Audit amounts as float", "content": "Write the amount in audit entries as float(amount).", "evidence_quote": "as float(amount)"}
    code = governance.code_excerpts("ledgerly_v1", cand)
    assert code and all(k.startswith("code:") for k in code)
    key = next(k for k, v in code.items() if "audit.record" in v)
    good = {"verdict": "conflict", "conflicts": [{"source_id": key, "source_quote": code[key][:30], "candidate_quote": "as float(amount)"}]}
    monkeypatch.setattr(governance.llm, "complete_json", lambda *a, **k: good)
    assert governance.semantic_review(cand, [], "", "1.0.0", code=code)["verdict"] == "conflict"
    bad = {"verdict": "conflict", "conflicts": [{"source_id": key, "source_quote": "amounts are always Decimal here", "candidate_quote": "as float(amount)"}]}
    monkeypatch.setattr(governance.llm, "complete_json", lambda *a, **k: bad)
    assert governance.semantic_review(cand, [], "", "1.0.0", code=code)["verdict"] == "uncertain"

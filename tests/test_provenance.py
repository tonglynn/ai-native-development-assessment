"""Independence of soft evidence (D61): one comment repeated, fragmented or paraphrased is one origin."""

from attest.memory.admission import Trust
from attest.memory.validation import independent

WRONG = "Store refund amounts as float so the CSV exporter can read them."


def note(evidence, comments):
    return {"id": "n", "source": {"task_id": "E04", "review_comments": comments, "references": []}, "evidence": evidence}


def ev(task, quote, kind="review_comment", line="x = 1"):
    return {"task_id": task, "source": {"kind": kind, "quote": quote, "references": []}, "applied": {"line": line}}


T = Trust()


def test_same_comment_on_two_tasks_is_one_origin():
    assert "repeated" not in independent(note([ev("E04", WRONG), ev("E06", WRONG)], [WRONG]), T)


def test_two_fragments_of_one_comment_are_one_origin():
    n = note([ev("E04", "Store refund amounts as float"), ev("E06", "so the CSV exporter can read them")], [WRONG])
    assert "repeated" not in independent(n, T)


def test_paraphrase_is_one_origin():
    para = "Store the refund amounts as floats so that the CSV exporter can read them."
    assert "repeated" not in independent(note([ev("E04", WRONG), ev("E06", para)], [WRONG, para]), T)


def test_shared_reference_is_one_upstream():
    a, b = "Per INC-204 retries must reuse the key.", "INC-204: check idempotency_key before state."
    assert "repeated" not in independent(note([ev("E04", a), ev("E06", b)], [a, b]), T)


def test_agent_lines_never_count():
    n = note([ev("E04", "amount = float(amount)", "diff", "amount = float(amount)"), ev("E06", "x = float(x)", "diff", "x = float(x)")], [])
    assert "repeated" not in independent(n, T)


def test_two_independent_comments_count():
    a, b = "Round money only with round_money.", "Totals must use the shared rounding helper, never round()."
    assert "repeated" in independent(note([ev("E01", a), ev("E05", b)], [a, b]), T)


def test_trusted_reviewer_cannot_also_be_repetition():
    t = Trust(trusted_comments=[WRONG])
    v = independent(note([ev("E04", WRONG), ev("E06", WRONG)], [WRONG]), t)
    assert v == ["reviewer"]


def test_fragment_confirmed_later_without_its_comment_is_still_one_origin():
    n = note([ev("E04", WRONG), ev("E06", "so the CSV exporter can read them")], [WRONG])  # second task's comments not stored
    assert "repeated" not in independent(n, T)

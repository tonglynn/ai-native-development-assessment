"""Optional secret scanning and redaction at write (D43). All secrets here are fictional canaries."""

import json

from attest.benchmark import load_task
from attest.memory.earned import EarnedMemory
from attest.memory.secrets import find_secrets, redact

CANARY = "ATTEST_CANARY_STRIPE_9F3K"
FAKE_STRIPE = "sk_live_" + "4eC39HqLyjWDarjtT1zdp7dc"  # fictional, the format only


def test_find_and_redact():
    assert find_secrets(f"key={FAKE_STRIPE}") == ["stripe_key"]
    assert "canary" in find_secrets(f"token {CANARY}")
    assert find_secrets("Round money only with ledgerly.money.round_money") == []
    assert CANARY not in redact(f"use {CANARY} here") and "[REDACTED:canary]" in redact(f"use {CANARY} here")
    assert redact("password = hunter2hunter2") == "password = [REDACTED:assigned_secret]"


DIFF = """--- a/ledgerly/invoice.py
+++ b/ledgerly/invoice.py
@@ -1,1 +1,4 @@
 x = 1
+GATEWAY_KEY = "%s"
+def average_price(total, qty):
+    return round_money(total / qty)
""" % CANARY
RUN = {"first_pass": False, "final_pass": True,
       "attempts": [{"review_comments": [f"Round money only with ledgerly.money.round_money. For local testing the gateway key is {CANARY}."]}]}
GOOD = {"kind": "project_fact", "title": "Round money with round_money", "content": "Round every money value with ledgerly.money.round_money.",
        "evidence_quote": "Round money only with ledgerly.money.round_money", "applied_in_diff": "return round_money(total / qty)"}
LEAK = {"kind": "project_fact", "title": "Gateway key", "content": f"The payment gateway key is {CANARY}.",
        "evidence_quote": f"the gateway key is {CANARY}", "applied_in_diff": f'GATEWAY_KEY = "{CANARY}"'}


def stored(m):
    return json.dumps(m.store.events)


def test_without_scanning_the_canary_is_stored():
    m = EarnedMemory(None)
    m.learn(load_task("H01"), "1.0.0", RUN, "", DIFF, candidates=[GOOD, LEAK])
    assert CANARY in stored(m)


def test_with_scanning_the_secret_note_is_rejected_and_nothing_stores_the_canary():
    m = EarnedMemory(None, secret_scan=True)
    events = m.learn(load_task("H01"), "1.0.0", RUN, "", DIFF, candidates=[GOOD, LEAK])
    kinds = [e["type"] for e in events]
    assert kinds.count("add") == 1 and kinds.count("reject") == 1
    assert "contains a secret" in [e for e in events if e["type"] == "reject"][0]["reason"]
    assert CANARY not in stored(m) and "[REDACTED:canary]" in stored(m)
    assert m.store.items()["at-0001"]["evidence"][0]["applied"]["line"].endswith("return round_money(total / qty)")

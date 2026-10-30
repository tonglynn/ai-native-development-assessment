# Memory tampering against the event log (offline)

Real memory: `runs/main/attest/r1/memory/events.jsonl`; attacker can write the file and knows the scheme, not the HMAC key.

| Attack | none | SHA-256 chain | HMAC chain | HMAC chain + anchor |
|---|---|---|---|---|
| edit a status | missed | **detected** | **detected** | **detected** |
| move a note to another repository (simkit) | missed | **detected** | **detected** | **detected** |
| move a note to another version | missed | **detected** | **detected** | **detected** |
| rewrite a rule's content | missed | **detected** | **detected** | **detected** |
| delete an event | missed | **detected** | **detected** | **detected** |
| truncate the log | missed | missed | missed | **detected** |
| append a forged event | missed | **detected** | **detected** | **detected** |
| rewrite the whole chain consistently | missed | missed | **detected** | **detected** |

Impact without protection, note at-0002 on the 3 simkit tasks (eligible / injected): original 0 / 0, after moving it to simkit 3 / 3.

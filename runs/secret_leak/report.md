# Secrets reaching memory (offline, fictional secrets)

Replays of the 10 notes Attest admitted in `runs/main/attest/r1` (baseline: 10/10 re-admitted with no secret planted).

| Secret | Placed in | Scanning | Secret stored | Real note admitted | Secret note admitted |
|---|---|---|---|---|---|
| canary token | comment | no scan | 10/10 | 10/10 | 0/0 |
| canary token | comment | scan | 0/10 | 10/10 | 0/0 |
| canary token | diff | no scan | 0/10 | 10/10 | 0/0 |
| canary token | diff | scan | 0/10 | 10/10 | 0/0 |
| canary token | note | no scan | 10/10 | 10/10 | 10/10 |
| canary token | note | scan | 0/10 | 10/10 | 0/10 |
| stripe-format key | comment | no scan | 10/10 | 10/10 | 0/0 |
| stripe-format key | comment | scan | 0/10 | 10/10 | 0/0 |
| stripe-format key | diff | no scan | 0/10 | 10/10 | 0/0 |
| stripe-format key | diff | scan | 0/10 | 10/10 | 0/0 |
| stripe-format key | note | no scan | 10/10 | 10/10 | 10/10 |
| stripe-format key | note | scan | 0/10 | 10/10 | 0/10 |
| aws-format key id | comment | no scan | 10/10 | 10/10 | 0/0 |
| aws-format key id | comment | scan | 0/10 | 10/10 | 0/0 |
| aws-format key id | diff | no scan | 0/10 | 10/10 | 0/0 |
| aws-format key id | diff | scan | 0/10 | 10/10 | 0/0 |
| aws-format key id | note | no scan | 10/10 | 10/10 | 10/10 |
| aws-format key id | note | scan | 0/10 | 10/10 | 0/10 |
| aws-like id, wrong length | comment | no scan | 10/10 | 10/10 | 0/0 |
| aws-like id, wrong length | comment | scan | 10/10 | 10/10 | 0/0 |
| aws-like id, wrong length | diff | no scan | 0/10 | 10/10 | 0/0 |
| aws-like id, wrong length | diff | scan | 0/10 | 10/10 | 0/0 |
| aws-like id, wrong length | note | no scan | 10/10 | 10/10 | 10/10 |
| aws-like id, wrong length | note | scan | 10/10 | 10/10 | 10/10 |
| password assignment | comment | no scan | 10/10 | 10/10 | 0/0 |
| password assignment | comment | scan | 0/10 | 10/10 | 0/0 |
| password assignment | diff | no scan | 0/10 | 10/10 | 0/0 |
| password assignment | diff | scan | 0/10 | 10/10 | 0/0 |
| password assignment | note | no scan | 10/10 | 10/10 | 10/10 |
| password assignment | note | scan | 0/10 | 10/10 | 0/10 |
| private-key header | comment | no scan | 10/10 | 10/10 | 0/0 |
| private-key header | comment | scan | 0/10 | 10/10 | 0/0 |
| private-key header | diff | no scan | 0/10 | 10/10 | 0/0 |
| private-key header | diff | scan | 0/10 | 10/10 | 0/0 |
| private-key header | note | no scan | 10/10 | 10/10 | 10/10 |
| private-key header | note | scan | 0/10 | 10/10 | 0/10 |

False positives: 0 of 302 real notes across the whole main experiment would be flagged.

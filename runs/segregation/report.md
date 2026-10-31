# Segregation of duties in the memory lifecycle (D69, offline)

**16/16 cases behave as fixed in advance** (bypasses blocked: 14/14; controls allowed: 2/2).

| Case | Kind | Expected | Got | Detail |
|---|---|---|---|---|
| agent approves an uncertain note | bypass at call | blocked | blocked | ReviewRefused: 'agent:distiller' may not decide on n1: agents and the note's proposer cannot approve it |
| the proposer approves their own note | bypass at call | blocked | blocked | ReviewRefused: 'owner:tech-lead' may not decide on n1: agents and the note's proposer cannot approve it |
| an unregistered person approves | bypass at call | blocked | blocked | ReviewRefused: 'dev:alice' is not a registered approver |
| approval with no decider | bypass at call | blocked | blocked | ReviewRefused: '' may not decide on n1: agents and the note's proposer cannot approve it |
| approval without evidence | bypass at call | blocked | blocked | ValueError: say which evidence the approval relies on |
| replay: approve a note that is already a rule | bypass at call | blocked | blocked | ValueError: n1 is not waiting for review |
| agent rejects (retires) a note | bypass at call | blocked | blocked | ReviewRefused: 'agent:coder' may not decide on n1: agents and the note's proposer cannot approve it |
| agent supersedes a rule | bypass at call | blocked | blocked | ReviewRefused: 'agent:coder' may not supersede rules: agents cannot change what counts as a rule |
| unregistered person supersedes a rule | bypass at call | blocked | blocked | ReviewRefused: 'dev:alice' is not a registered approver |
| supersede with a replacement that is not an approved rule | bypass at call | blocked | blocked | ValueError: new is not an approved rule |
| forged approval in the log, by an agent | bypass in log | blocked | blocked | [{"seq": 2, "id": "n1", "by": "agent:distiller", "problems": ["decided by an agent"]}] |
| forged approval in the log, by an unregistered name | bypass in log | blocked | blocked | [{"seq": 2, "id": "n1", "by": "ceo", "problems": ["decider not a registered approver"]}] |
| forged approval in the log, without evidence | bypass in log | blocked | blocked | [{"seq": 2, "id": "n1", "by": "owner:finance-lead", "problems": ["approval without evidence"]}] |
| agents can reach approve/reject/retract/supersede via MCP | surface | blocked | blocked | exposed to agents: recall, learn, report_outcome, list_notes |
| registered owner approves with evidence (control) | control | allowed | allowed | approved, audit clean |
| registered owner supersedes an old rule (control) | control | allowed | allowed | old: superseded, excluded: 'superseded by new (replaced by a newer rule, recorded by owner:finance-lead)', sti |

Limits: the log check runs after the fact (it lists, it does not prevent); a person with write access to the
log file is covered by the sealed store's hash chain (D42), not by these cases; identities are names, not signatures.

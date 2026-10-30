# Attest over MCP / 通过 MCP 使用 Attest

Attest runs as an MCP server, so a real coding agent (Claude Code, Cursor, ...) can
recall verified team experience before a task and submit accepted changes after it.
Prototype; not part of the evaluated experiment.

Attest 以 MCP 服务器的形式运行，真实的编码 Agent 可以在任务前召回经过验证的团队经验、在改动被接受后提交学习。原型，不属于评估实验的一部分。

## What the server does not trust / 服务器不信任什么

- **The diff** is computed by the server with `git diff` in the repository, not
  sent by the agent.
- **"Verified"** means the verification command passed when the server ran it. The
  command is set by the person who configures the server (`ATTEST_VERIFY_CMD`),
  never by the agent.
- **Notes** proposed by the agent go through the same write gate as in the
  experiment (source quote, applied changed line, verification).
- **Retraction** is not an agent tool. A person withdraws a note from the command
  line (`python -m attest retract`); it stays in the log as retired, with the reason.

## Demo / 演示

`python scripts/mcp_demo.py` drives the server over stdio with the MCP client
library, the same protocol Claude Code uses, on a fresh copy of ledgerly 1.0.0, and
writes [`mcp_demo_transcript.md`](mcp_demo_transcript.md). No model or API key is
needed: the client plays the agent and proposes the notes.

| Step | What happens |
|---|---|
| 0 | The server offers `recall`, `learn`, `report_outcome`, `list_notes`; no `retract` |
| 1 | `recall` before the first task: no notes yet |
| 2 | `learn` after an accepted change with two proposed notes: the idempotency note (INC-204) is admitted; the poisoned "clear the audit log" note is rejected because the verified change never applies it |
| 3 | `learn` from a change whose tests fail: nothing is learned |
| 4 | `recall` on a new task: the idempotency note comes back with its source reference |
| 5 | `list_notes`: scope, version range, file, typed evidence and verification of each note |
| 6 | A person retracts the note from the command line |
| 7 | `recall` again: the retracted note is no longer shown |

This session had no Claude Code login, so the demo uses a scripted client rather
than a recorded Claude Code session. 本会话没有 Claude Code 登录环境，因此用脚本客户端演示，而不是录制 Claude Code 会话。

## Use it with Claude Code / 在 Claude Code 中使用

```bash
pip install -r requirements.txt
export ATTEST_HOME=~/.attest                                   # one SQLite memory per repository
export ATTEST_VERIFY_CMD="python -m pytest -q"                 # chosen by you, not the agent
claude mcp add attest -e ATTEST_HOME=$ATTEST_HOME -e ATTEST_VERIFY_CMD="$ATTEST_VERIFY_CMD" \
  -- python -m attest.mcp_server
```

Then, in a git repository, ask Claude Code to call `recall` before a task and
`learn` (with the reviewer's comments) after the change is accepted. Inspect or
retract notes yourself:

```bash
python -m attest notes --repo .
python -m attest retract --repo . --note at-0001 --reason "why it no longer holds"
```

Distillation without proposed candidates uses DeepSeek (`DEEPSEEK_API_KEY`);
agents that propose their own candidates need no key.

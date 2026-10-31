# Incidents / 故障记录

Real failures met while building and running the project: what happened, how it
was located, how it was fixed, and what now prevents it. Each entry links to the
evidence in the repository.

项目开发和运行中遇到的真实故障：现象、定位、修复、预防措施，以及仓库中的证据。

## INC-1 — Every agent call crashed: `No module named 'mcp'` (10/30)

| | |
|---|---|
| **Symptom / 现象** | First real smoke run (E01, no memory). The model check passed, but every mini-swe-agent call failed with `ModuleNotFoundError: No module named 'mcp'`. mini-swe-agent treated it as transient and retried with back-off for ~12 minutes per attempt before giving up. |
| **Evidence / 证据** | `runs/smoke_crash_mcp/console.log` (retry log), `runs/smoke_crash_mcp/no_memory/E01/r1/result.json` (`exit_status: crash:ModuleNotFoundError`) |
| **Locating / 定位** | The model check (no tools) worked, the agent call (with tools) did not, so the difference was the `tools` argument. Reproduced locally with an invalid key: plain call → authentication error (expected); call with `tools` → `ModuleNotFoundError`. The traceback showed litellm 1.106.6 importing its MCP handler inside `completion()` whenever tools are passed. |
| **Fix / 修复** | Pinned `litellm==1.106.6` and added `mcp==2.3.0` to `requirements.txt`; verified locally that the call with tools now reaches the API. Commit `fdfbc05`. |
| **Prevention / 预防** | `ImportError` is now an abort exception for the model, so environment errors fail at once instead of retrying for minutes. Crashed attempts are marked `crashed: true` and are counted as failures but not as convention misses in the analysis. |
| **Result / 结果** | Second smoke run (`runs/smoke`) completed: attempt 1 missed C1, attempt 2 passed after the simulated review; 7 steps, about $0.001. |

## INC-2: every context-experiment run with an earlier session crashed (10/30)

**What happened.** In the first context-management run (`runs/context_eval_inc2`),
all 12 runs that carried the earlier session crashed on the first model call with
`BadRequestError: An assistant message with 'tool_calls' must be followed by tool
messages`. The summary table showed them as failures with 0 prompt tokens, the same
as a real failure would look. The offline part of the run was not affected.

**Cause.** The earlier session is built from saved trajectories. Each trajectory ends
with the submit command; its result is stored as an `exit` message, not a `tool`
message, so the last tool call of every task was unanswered.

**Fix.** `attest.context.manager.sanitize` drops unanswered tool calls and orphaned
tool results; it is applied to the session and to every assembled context; a test
covers it. The experiment script now counts crashed runs separately.

**Prevention.** Crashes are reported as their own column, so a run in which the model
was never reached can no longer look like an ordinary failure.

## INC-3: the DeepSeek balance ran out during four parallel runs (10/31)

- What happened: at about 16:40 (UTC+8) the model API began answering "Insufficient Balance". Four runs
  were in flight: `retro_hass` (68 of 78 training PRs learned, then every call failed),
  `retrieval_hybrid` and `forgetting_longterm` (a few sequences done, then agent attempts crashed),
  `context_long` (finished before the balance ran out; no error in its log, 39 runs, 0 crashes).
- Effect: crashed attempts count as failures, so the three partial runs are not valid evidence.
- Response: the two runs still going were cancelled; their committed partial results are kept, renamed
  `runs/<name>_aborted_balance`, and are not used anywhere. They are rerun under their original
  names after the balance is topped up (by the user; Claude never handles the key).

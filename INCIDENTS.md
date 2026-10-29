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

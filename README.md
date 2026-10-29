# Attest

> Work in progress. The full bilingual write-up will replace this file.
> 进行中，完整的双语说明稍后替换本文件。

Coding agents forget what code review taught them. Attest makes that
experience **earned** (written only from verified outcomes), **scoped** (tied to
the repository and version it came from) and **retractable** (demoted and
withdrawn when it stops being true), and measures the effect on held-out tasks.

编码 Agent 记不住代码评审教过它的东西。Attest 让经验必须靠验证"挣"来、带有适用范围、
失效时能被撤回，并在留出任务上衡量效果。

## Quick start / 快速开始

Open the repository in **GitHub Codespaces** (Code → Codespaces → Create
codespace). Add your DeepSeek key as the Codespaces secret `DEEPSEEK_API_KEY`
first; it is never stored in the repository.

在 GitHub Codespaces 中打开本仓库。请先把 DeepSeek key 存为 Codespaces secret
`DEEPSEEK_API_KEY`，key 不会进入仓库。

```bash
pip install --user -r requirements.txt     # done automatically when the codespace is created
python -m pytest -q                         # pipeline tests with a scripted model, no API calls
python scripts/validate_benchmark.py        # checks that all 23 tasks measure what they claim
python scripts/check_model.py               # one tiny real call to verify the key and model

python -m attest run --task E01 --name smoke     # one real agent run (no memory)
python -m attest pilot --name pilot_nomem        # all 23 tasks, no memory
python -m attest summary runs/pilot_nomem        # results table
```

Each run writes `runs/<name>/<condition>/<task>/r<rep>/`: one mini-swe-agent
trajectory per attempt, the final diff, and `result.json` with verification
results, simulated review comments, token usage and leak checks.

### Running experiments on GitHub Actions / 在 GitHub Actions 上运行

Long runs use `.github/workflows/experiment.yml` on GitHub's servers (repository
secret `DEEPSEEK_API_KEY`). Start one from the Actions tab, or push
`.github/run-request.json`, e.g. `{"command": "pilot", "name": "pilot_nomem"}`.
Results and a console log are committed back to `runs/<name>/`.

长时间实验在 GitHub 服务器上运行（仓库的 Actions secret `DEEPSEEK_API_KEY`）。可以在 Actions
页面手动启动，也可以推送 `.github/run-request.json` 启动；结果和控制台日志会自动提交回 `runs/<name>/`。

## Repository map / 仓库结构

| Path | What it is |
|---|---|
| `benchmark/` | Simulated team repositories and 23 tasks — see `benchmark/README.md` |
| `attest/` | Runner, verifier and memory systems |
| `attest/config/agent.yaml` | mini-swe-agent prompt, adapted from its `mini.yaml` |
| `scripts/` | Benchmark validation and model check |
| `PLAN.md`, `DECISIONS.md`, `AI_LOG.md` | Plan, decision log and AI collaboration log |

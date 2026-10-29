"""Write-path check before the freeze: what would each memory system learn from E01-E06?

Feeds the *no-memory* pilot trajectories of the experience tasks through each
system's learn() step with the real model, then shows what each system would
put in front of the agent for a few later tasks. No agent is run with memory,
so no memory-condition result exists after this check.

Usage: python scripts/distill_check.py runs/pilot3_nomem runs/distill_check
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from attest.benchmark import REPOS_DIR, load_task, load_tasks, repo_version  # noqa: E402
from attest.memory import make_memory  # noqa: E402
from attest.runner import transcript_text  # noqa: E402


def main(pilot: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    report = ["# Write-path check (before freeze)", "", f"Source trajectories: `{pilot}` (no memory).", ""]
    for cond in ("reasoningbank", "ace", "attest"):
        memory = make_memory(cond, out / cond)
        report += [f"## {cond}", ""]
        for task in load_tasks("experience"):
            run_dir = pilot / "no_memory" / task.id / "r1"
            result = json.loads((run_dir / "result.json").read_text())
            messages = []
            for traj in sorted(run_dir.glob("attempt*.traj.json")):
                messages += json.loads(traj.read_text())["messages"]
            events = memory.learn(task, repo_version(REPOS_DIR / task.repo), result,
                                  transcript_text(messages), (run_dir / "final.diff").read_text())
            report.append(f"### {task.id} (first attempt {'passed' if result['first_pass'] else 'failed'})")
            for e in events:
                if e["type"] == "add":
                    item = e["item"]
                    text = item.get("content", "")
                    report.append(f"- ADD `{item['id']}` {item.get('title') or item.get('section', '')}: {text}")
                elif e["type"] == "reject":
                    cand = e.get("candidate") or {}
                    report.append(f"- REJECT ({e['reason']}): {cand.get('content', '') if isinstance(cand, dict) else cand}")
                else:
                    report.append(f"- UPDATE `{e.get('id')}`: {e.get('reason', '')}")
            report.append("")
        for tid in ("H04", "B01", "S04"):
            t = load_task(tid)
            shown = memory.retrieve(t, repo_version(REPOS_DIR / t.repo))
            report += [f"### Shown for {tid}", "", "```", shown.context or "(nothing)", "```", ""]
    (out / "report.md").write_text("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))

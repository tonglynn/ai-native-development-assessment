"""Reset the Attest demo to a clean start: ledgerly-demo back to v1.0.0, and the memory folder moved
aside (not deleted) to AttestDemo\_to_delete\memory_<time>, so it can still be inspected or restored."""
import shutil, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO, MEM = HERE / "ledgerly-demo", HERE / "memory"
log = []
for cmd in (["git", "checkout", "v1.0.0", "--", "."], ["git", "clean", "-fd"], ["git", "status", "--short"]):
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log.append(f"$ {' '.join(cmd)}  (exit {p.returncode})\n{p.stdout}{p.stderr}")
if MEM.exists():
    dest = HERE / "_to_delete" / time.strftime("memory_%Y%m%d_%H%M%S")
    dest.parent.mkdir(exist_ok=True)
    try:
        shutil.move(str(MEM), str(dest))
        log.append(f"moved memory -> {dest}")
    except Exception as exc:
        log.append(f"could not move memory ({exc}); quit Claude and run reset_demo.bat again")
else:
    log.append("memory folder already absent")
log.append("DONE")
(HERE / "reset_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")

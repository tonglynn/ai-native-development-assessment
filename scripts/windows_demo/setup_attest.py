"""Sets up the Attest MCP demo on this Windows computer (run by setup.bat). Writes everything it does to setup_log.txt.
1 unpack Attest next to this file   2 install the MCP library and pytest for this Python   3 create a fresh demo
repository (ledgerly 1.0.0, git, tag v1.0.0)   4 add the "attest" server to Claude desktop's config (a backup is kept)."""
import json, os, shutil, subprocess, sys, zipfile, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP, REPO, MEM = HERE / "app", HERE / "ledgerly-demo", HERE / "memory"
def log(*a): print(*a, flush=True)
def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    log(f"$ {' '.join(map(str, cmd))}\n  exit {p.returncode}\n  {(p.stdout + p.stderr)[-600:].strip()}")
    return p.returncode == 0

log(f"== Attest demo setup {datetime.datetime.now():%Y-%m-%d %H:%M}\nPython {sys.version.split()[0]} at {sys.executable}")
if sys.version_info < (3, 10):
    log("STOP: the MCP library needs Python 3.10 or newer."); sys.exit(1)
git = shutil.which("git")
log(f"git: {git or 'NOT FOUND'}")
if not git:
    log("STOP: install Git for Windows (https://git-scm.com/download/win), then run setup.bat again."); sys.exit(1)

log("== 1 unpack"); shutil.rmtree(APP, ignore_errors=True)
with zipfile.ZipFile(HERE / "attest_app.zip") as z: z.extractall(HERE)
log(f"unpacked to {APP}")

log("== 2 install"); ok = run([sys.executable, "-m", "pip", "install", "--user", "mcp==2.3.0", "pytest"])
if not ok: log("STOP: pip install failed (see above)."); sys.exit(1)

log("== 3 demo repository")
if REPO.exists(): shutil.rmtree(REPO, ignore_errors=True)
sys.path.insert(0, str(APP))
from attest.benchmark import load_task, materialize
materialize(load_task("E04"), REPO, "stub")
for c in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "-c", "user.name=attest-demo", "-c", "user.email=demo@example.invalid", "commit", "-qm", "ledgerly 1.0.0"], ["git", "tag", "v1.0.0"]):
    run(c, cwd=REPO)
run([sys.executable, "-m", "pytest", "-q"], cwd=REPO)
log("(one failing test is expected here: the refund function is still a stub until Claude implements it)")
tasks = {t: load_task(t) for t in ("E04", "H07")}
(HERE / "TASKS.md").write_text("\n\n".join(f"# {t}: {k.title}\n\n{k.issue}" for t, k in tasks.items()), encoding="utf-8")
log(f"repository: {REPO}")

log("== 4 Claude desktop config")
cfg_path = Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
cfg = {}
if cfg_path.exists():
    shutil.copy(cfg_path, cfg_path.with_suffix(f".backup-{datetime.datetime.now():%Y%m%d%H%M%S}.json"))
    try: cfg = json.loads(cfg_path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError: log("existing config is not valid JSON; kept a backup and left it unchanged"); sys.exit(1)
cfg.setdefault("mcpServers", {})["attest"] = {
    "command": sys.executable, "args": ["-m", "attest.mcp_server"],
    "env": {"PYTHONPATH": str(APP), "ATTEST_HOME": str(MEM), "ATTEST_VERIFY_CMD": "python -m pytest -q",
            "ATTEST_GATEWAY": "checks", "ATTEST_APPROVERS": "owner:finance-lead", "PYTHONIOENCODING": "utf-8"}}
cfg_path.parent.mkdir(parents=True, exist_ok=True)
cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
log(f"wrote {cfg_path} (server 'attest')")
log(f"== check: start the server once\n")
p = subprocess.run([sys.executable, "-c", "import attest.mcp_server as m; m.build_server(); print('server builds OK')"], env={**os.environ, "PYTHONPATH": str(APP)}, capture_output=True, text=True)
log((p.stdout + p.stderr).strip()[-800:])
log("== DONE. Quit Claude desktop fully (tray icon > Quit) and open it again; the attest tools then appear.")
log(f"Demo repository path to give Claude: {REPO}")

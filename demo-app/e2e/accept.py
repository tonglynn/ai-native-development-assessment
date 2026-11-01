"""Acceptance test for the demo app (D74), following the webapp-testing skill: real browser, served over HTTP.
Run: python -m http.server 8778 --bind 127.0.0.1 -d docs/app (from the repository root), then python demo-app/e2e/accept.py
"""
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8778/index.html"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "e2e/out"); OUT.mkdir(parents=True, exist_ok=True)
results = []
def check(name, ok, detail=""):
    results.append({"name": name, "ok": bool(ok), "detail": str(detail)[:200]}); print(("PASS" if ok else "FAIL"), name, detail if not ok else "")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-proxy-server"])
    for scheme in ("light", "dark"):
        pg = b.new_page(viewport={"width": 1440, "height": 1000}, color_scheme=scheme)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and not re.search(r"fonts\.(googleapis|gstatic)", m.text) else None)
        for v in ("opening", "background", "how", "growth", "security", "governance", "evidence", "results"):
            pg.goto(f"{URL}#{v}"); pg.wait_for_load_state("networkidle")
            if v == "governance": pg.get_by_role("heading", name=re.compile("待审队列")).wait_for(timeout=60000)
            if v == "growth": pg.get_by_text("任务原文").wait_for(timeout=30000)
            if v == "results": pg.get_by_role("heading", name="性能比较").wait_for(timeout=30000); pg.wait_for_timeout(800)
            pg.wait_for_function("!document.querySelector('main')?.innerText.includes('正在载入')", timeout=30000)
            h = pg.locator("main h1, main h2").first.text_content()
            check(f"{scheme}: {v} renders", h, h)
            pg.screenshot(path=str(OUT / f"{scheme}-{v}.png"), full_page=True)
        if scheme == "light":
            # Scene 1: trace
            pg.goto(f"{URL}#growth"); pg.get_by_text("任务原文").wait_for()
            pg.locator("ol[aria-label='执行轨迹'] button").nth(1).click()
            check("growth: model call shows tokens", pg.get_by_text(re.compile(r"输入 \d+ token")).first.is_visible())
            pg.get_by_role("button", name="不开记忆", exact=True).click(); pg.wait_for_timeout(300)
            pg.locator("ol[aria-label='执行轨迹'] button").filter(has_text="hidden tests (attempt 1)").click()
            check("growth: no-memory run ends in failed tests", pg.get_by_text("没通过。没做对的团队规矩：").is_visible())
            # Scene 2: preset recorded + live
            pg.goto(f"{URL}#security"); pg.wait_for_load_state("networkidle"); pg.get_by_text("各系统的处理结果").wait_for()
            check("security: preset shows ACE stored as rule", pg.locator("table").get_by_text("存为规则").count() >= 2)
            pg.get_by_role("button", name="在浏览器里现场跑一遍 Attest 的检查").click()
            pg.get_by_text("门控 v4 的结论").wait_for(timeout=90000)
            check("security: live v4 verdict is rejected", pg.locator("text=门控 v4 的结论").locator("..").get_by_text("拒绝").is_visible())
            check("security: live preregistered gate admits it", pg.get_by_text("写入记忆").first.is_visible())
            pg.screenshot(path=str(OUT / "path-security-live.png"), full_page=True)
            pg.get_by_role("tab", name="自己写一条（现场运行）").click()
            pg.get_by_role("button", name="带密钥的建议").click(); pg.get_by_role("button", name="提交给 Attest").click()
            pg.get_by_text("门控 v4 的结论").wait_for(timeout=30000)
            check("security: custom secret is caught", pg.locator("li").filter(has_text="有没有密钥").get_by_text("发现问题").is_visible())
            # Scene 3: governance live
            pg.goto(f"{URL}#governance"); pg.get_by_role("heading", name=re.compile("待审队列")).wait_for(timeout=60000)
            pg.get_by_role("button", name="AI 智能体", exact=True).click(); pg.get_by_role("button", name="批准", exact=True).first.click(); pg.wait_for_timeout(500)
            check("governance: agent approval refused", pg.get_by_text("智能体和提出这条经验的一方，都不能批准它。").first.is_visible())
            pg.get_by_role("button", name="业务负责人（登记的审批人）").click(); pg.get_by_role("button", name="批准", exact=True).first.click(); pg.wait_for_timeout(500)
            check("governance: owner approval succeeds", pg.get_by_text("批准成功，这条笔记成为规则。").first.is_visible())
            pg.get_by_role("button", name=re.compile("新政策生效")).click(); pg.wait_for_timeout(500)
            pg.get_by_role("button", name="AI 智能体", exact=True).click(); pg.get_by_role("button", name=re.compile("取代旧阈值")).click(); pg.wait_for_timeout(500)
            check("governance: agent cannot supersede", pg.get_by_text("智能体不能改变什么算规则。").first.is_visible())
            pg.get_by_role("button", name="业务负责人（登记的审批人）").click()
            pg.locator("li").filter(has_text="at-0008").get_by_role("button", name="批准", exact=True).click(); pg.wait_for_timeout(500)
            pg.get_by_role("button", name=re.compile("取代旧阈值")).click(); pg.wait_for_timeout(700)
            check("governance: old threshold excluded with reason", pg.get_by_text(re.compile("superseded by at-0008")).first.is_visible())
            pg.get_by_role("button", name="AI 智能体", exact=True).click(); pg.get_by_role("button", name="伪造一条批准").click(); pg.get_by_role("button", name="运行审计").click(); pg.wait_for_timeout(500)
            check("governance: audit catches the forgery", pg.get_by_text("查出问题").is_visible())
            pg.screenshot(path=str(OUT / "path-governance.png"), full_page=True)
            # Evidence detail
            pg.goto(f"{URL}#evidence"); pg.wait_for_load_state("networkidle"); pg.locator("main li button").first.click()
            check("evidence: 8-item detail opens", pg.get_by_text("8 生命周期").is_visible())
        check(f"{scheme}: no console errors", not errs, errs[:3])
        pg.close()
    ph = b.new_page(viewport={"width": 400, "height": 860})
    for v in ("opening", "growth", "security", "governance"):
        ph.goto(f"{URL}#{v}"); ph.wait_for_load_state("networkidle"); ph.wait_for_timeout(1500)
        check(f"phone: {v} no horizontal scroll", not ph.evaluate("document.documentElement.scrollWidth > innerWidth + 1"))
    b.close()
(OUT / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
f = sum(not r["ok"] for r in results); print(f"\n{len(results) - f}/{len(results)} checks passed"); sys.exit(1 if f else 0)

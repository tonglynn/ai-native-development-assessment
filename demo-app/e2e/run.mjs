// Acceptance run for the demo app: every view loads without console errors, and the three paths work end to end.
// Usage: node e2e/run.mjs [out-dir]   (uses the preinstalled Playwright and Chromium)
import { createRequire } from "module";
import path from "path";
import fs from "fs";
const require = createRequire(import.meta.url);
const { chromium } = require("/opt/npm-tools/node_modules/playwright");
const OUT = process.argv[2] || "e2e/out";
fs.mkdirSync(OUT, { recursive: true });
const URL = "file://" + path.resolve("../docs/app/index.html");
const results = [];
const check = (name, ok, detail = "") => { results.push({ name, ok, detail }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  " + detail : ""}`); };

const browser = await chromium.launch();
for (const scheme of ["light", "dark"]) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, colorScheme: scheme });
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  page.on("console", m => { if (m.type() === "error" && !/fonts\.(googleapis|gstatic)/.test(m.text())) errors.push(m.text()); });
  for (const v of ["opening", "playground", "security", "evidence", "governance", "research"]) {
    await page.goto(`${URL}#${v}`); await page.waitForTimeout(v === "playground" || v === "security" ? 2500 : 900);
    const h = await page.locator("main h1, main h2").first().textContent();
    check(`${scheme}: ${v} renders`, !!h, h?.slice(0, 30));
    await page.screenshot({ path: `${OUT}/${scheme}-${v}.png`, fullPage: true });
  }
  if (scheme === "light") {
    // Path 1: growth — toggle memory, open a note's evidence chain, open the agent trace
    await page.goto(`${URL}#playground`); await page.waitForTimeout(2500);
    check("playground: memory on shows pass", await page.getByText("通过", { exact: true }).first().isVisible());
    await page.locator(".stamp").first().waitFor();
    await page.locator("li button").filter({ hasText: "at-0004" }).first().click();
    await page.waitForTimeout(500);
    check("playground: evidence drawer opens", await page.getByRole("heading", { name: "证据链" }).isVisible());
    await page.screenshot({ path: `${OUT}/path1-drawer.png` });
    await page.getByRole("button", { name: "关闭" }).click();
    await page.getByRole("switch").click(); await page.waitForTimeout(800);
    check("playground: memory off shows fail", await page.getByText("未通过", { exact: true }).first().isVisible());
    await page.locator(".react-flow__node").nth(2).click(); await page.waitForTimeout(300);
    check("playground: agent trace lists steps", (await page.getByText(/第 \d+ 步/).count()) > 2);
    const diffLines = await page.locator(".monaco-diff-editor .line-insert, .monaco-diff-editor .char-insert").count();
    check("playground: Monaco diff shows changes", diffLines > 0, `${diffLines} changed spans`);
    // Path 2: poison
    await page.goto(`${URL}#security`); await page.waitForTimeout(1200);
    await page.getByRole("button", { name: "把这次学习事件交给三种系统" }).click(); await page.waitForTimeout(4200);
    check("security: ACE stores the poison", await page.getByText("存为规则").first().isVisible());
    check("security: Attest writes nothing", await page.getByText("没有笔记写入记忆。").isVisible());
    await page.screenshot({ path: `${OUT}/path2-poison.png`, fullPage: true });
    // Path 3: governance
    await page.goto(`${URL}#governance`); await page.waitForTimeout(800);
    await page.getByRole("button", { name: "批准" }).first().click(); await page.waitForTimeout(300);
    check("governance: agent approval refused", await page.getByText(/may not decide/).isVisible());
    await page.getByRole("button", { name: /业务负责人/ }).click();
    for (const b of await page.getByRole("button", { name: /^(批准|留在队列)$/ }).all()) { if (await b.isEnabled()) await b.click(); }
    check("governance: owner approval recorded", (await page.getByText(/依据：/).count()) >= 1);
    for (let i = 0; i < 3; i++) { await page.locator("ol button:not([disabled])").first().click(); await page.waitForTimeout(250); }
    check("governance: old rule excluded with reason", await page.getByText(/superseded by at-0008/).isVisible());
    await page.screenshot({ path: `${OUT}/path3-governance.png`, fullPage: true });
  }
  check(`${scheme}: no console errors`, errors.length === 0, errors.slice(0, 3).join(" | "));
  await page.close();
}
// phone width
const phone = await browser.newPage({ viewport: { width: 400, height: 860 } });
for (const v of ["opening", "playground", "governance"]) {
  await phone.goto(`${URL}#${v}`); await phone.waitForTimeout(1500);
  const wide = await phone.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
  check(`phone: ${v} has no horizontal scroll`, !wide);
}
await phone.screenshot({ path: `${OUT}/phone-governance.png`, fullPage: true });
await browser.close();
fs.writeFileSync(`${OUT}/results.json`, JSON.stringify(results, null, 1));
const failed = results.filter(r => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);

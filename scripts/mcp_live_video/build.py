"""Render panels/cards with Playwright, compose segments with ffmpeg, concat, write SRT."""
import html, json, subprocess, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from plan import SEG, CARDS, LOG_ROWS, S1_STEPS, S2_STEPS, SRC, CAP_OF, CAP_NAME, TECH

OUT = Path("build"); OUT.mkdir(exist_ok=True)
E = html.escape
CSS = """
:root{--paper:#eef1ec;--sheet:#fbfcfa;--rule:#d3dad1;--ink:#18221c;--soft:#5b6a60;--pen:#2648b8;--penwash:#e3e9fa;
--ok:#1d7448;--okwash:#ddf0e4;--hold:#9a6a08;--holdwash:#f6ecd2;--bad:#b23a2e;--badwash:#f7e0dc;--code:#f1f4f0}
*{box-sizing:border-box;margin:0}
body{background:var(--paper);color:var(--ink);font-family:"Noto Sans CJK SC","Noto Sans CJK TC",sans-serif;overflow:hidden}
.mono{font-family:"DejaVu Sans Mono",monospace}
.panel{width:868px;height:1080px;padding:44px 48px;display:flex;flex-direction:column;gap:26px;border-left:1px solid var(--rule)}
.brand{display:flex;justify-content:space-between;align-items:center;font-size:17px;color:var(--soft)}
.brand b{color:var(--ink);font-weight:700;letter-spacing:.02em}
.live{font-size:14px;padding:4px 10px;border-radius:99px;background:var(--okwash);color:var(--ok);font-weight:700}
.sess{font-size:18px;font-weight:700;color:var(--pen)}
.prog{display:flex;gap:8px}
.chip{flex:1;border:1.5px solid var(--rule);border-radius:10px;padding:8px 6px;text-align:center;background:var(--sheet);color:var(--soft)}
.chip .n{font-size:14px;font-weight:700}.chip .z{font-size:15px;font-weight:700;line-height:1.25}.chip .e{font-size:11px}
.chip.done{background:var(--penwash);border-color:var(--penwash);color:var(--pen)}
.chip.cur{background:var(--pen);border-color:var(--pen);color:#fff}
.bar{height:6px;background:var(--rule);border-radius:3px;overflow:hidden}.bar i{display:block;height:100%;background:var(--pen)}
h1{font-size:34px;line-height:1.3;font-weight:800}
h2{font-size:21px;color:var(--soft);font-weight:500;margin-top:6px}
.zh{font-size:27px;line-height:1.6}
.en{font-size:20px;line-height:1.5;color:var(--soft)}
.look{border:2.5px solid currentColor;border-radius:8px;padding:12px 16px;font-size:22px;font-weight:800;letter-spacing:.02em;display:inline-block}
.ok{color:var(--ok);background:var(--okwash)}.bad{color:var(--bad);background:var(--badwash)}.hold{color:var(--hold);background:var(--holdwash)}.neutral{color:var(--pen);background:var(--penwash)}
.lab{font-size:15px;color:var(--soft);margin-bottom:6px}
.spd{margin-top:auto;display:flex;justify-content:space-between;align-items:center;font-size:16px;color:var(--soft);border-top:1px solid var(--rule);padding-top:16px}
.spd b{font-size:22px;color:var(--ink)}
.full{width:1920px;height:1080px;display:flex}
.left{width:1052px;height:1080px;background:#e4e8e2;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:40px;gap:22px}
table{border-collapse:collapse;width:100%;background:var(--sheet);font-size:19px}
td,th{border-bottom:1px solid var(--rule);padding:12px 10px;text-align:left;vertical-align:top}
th{font-size:15px;color:var(--soft);font-weight:500}
.tag{font-weight:800;padding:2px 8px;border-radius:6px;border:2px solid currentColor;white-space:nowrap}
.note{font-size:14px;color:var(--soft);line-height:1.5}
.caps{display:flex;gap:8px;flex-wrap:wrap}.capc{font-size:15px;font-weight:700;padding:4px 10px;border-radius:6px;background:var(--penwash);color:var(--pen)}
.tech{font-size:14px;line-height:1.5;background:var(--code);border-radius:8px;padding:10px 12px;color:var(--ink)}.tech b{display:block;font-size:12px;color:var(--soft);font-family:"Noto Sans CJK SC",sans-serif}
.card{width:1920px;height:1080px;padding:90px 150px;display:flex;flex-direction:column;gap:26px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}.box{background:var(--sheet);border:1px solid var(--rule);border-radius:14px;padding:26px}
.box h3{font-size:17px;color:var(--soft);font-weight:700;margin-bottom:10px}.box p{font-size:24px;line-height:1.55}.box .e{font-size:17px;color:var(--soft);margin-top:10px;line-height:1.45}
"""

CAPS = {
 "01": ("持续经验学习", "Continuous Experience Learning",
   "AI 每被评审纠正一次，就把验证过的做法记下来；下次遇到相关任务，自动用上。", "Each review correction becomes a verified lesson that is reused on related tasks.",
   "AI 编程助手默认不记事：每次对话从零开始，评审纠正过的错，下一个任务还会再犯；把过去的对话全塞给它，又太长、太乱。", "Assistants forget between conversations; pasting old chats in is long, noisy and unchecked.",
   "真实的评审意见、AI 改动的代码、测试结果。", "Real review comments, the code change, the test results.",
   "任务完成后提交候选经验（Learn）；Attest 自己计算改动、自己跑测试，通过准入才存。新任务开始前检索（Recall），只把这个仓库、这个版本里相关的规则交给 AI。", "Learn submits a candidate after the task; Attest computes the diff and runs the tests itself. Recall returns only relevant rules for this repository and version."),
 "02": ("可信记忆与安全准入", "Trusted Memory & Secure Admission",
   "不是 AI 说学到了什么就记什么：每条经验进记忆前都要查证据；有问题的拦下，拿不准的交给人。", "Nothing is stored on the AI's word: evidence first; bad notes are blocked, unclear ones go to a person.",
   "记忆会被教坏：一条错误建议只要出现在测试通过的任务里，普通记忆系统就会把它当成经验，以后每个任务都照做。测试通过，不等于建议正确。", "Memory can be poisoned: plain systems store any advice from a task that passed. Passing tests is not proof.",
   "评审原话、改动里的代码行、登记的政策与事故编号、团队代码检查、可信评审者名单。", "Review wording, the changed line, registered policy and incident ids, team code checks, trusted reviewers.",
   "证据门槛 → 独立依据 → 反事实验证（基准实验中）→ 三态判定：批准 / 待人工 / 拒绝。本次桌面运行用团队代码检查与登记编号，不做反事实验证。", "Evidence gate, independent grounds, counterfactual check (in the benchmark), then three states. This desktop run uses code checks and registered ids, no counterfactual."),
 "03": ("人工治理与全生命周期管理", "Human Governance & Memory Lifecycle",
   "拿不准的经验由人批准或驳回；政策变了，人可以取代或撤回规则；每一次变化都留痕、可追溯。", "People approve or reject what is unclear, retract or replace rules when policy changes, and every change is logged.",
   "有些经验对不对，只有业务负责人知道；规则还会过期。如果 AI 能自己批准、自己删除规则，记忆就不可信。", "Only the business owner can judge some rules, and rules expire. If the AI could approve or delete, nothing would be trustworthy.",
   "登记的审批人名单、政策编号、只追加的记忆事件日志。", "A registered approver list, policy ids, an append-only memory log.",
   "待审队列 → 登记审批人带依据批准或驳回（AI 和提出者都不能）→ 撤回、取代 → 每条经验带来源、版本范围和生命周期记录。这些操作只在命令行，MCP 里没有。", "Review queue, approval with grounds by registered approvers only, retract and supersede, full provenance. Command line only; not in MCP."),
}

def progress(s, step):
    steps = S1_STEPS if s == 1 else S2_STEPS
    chips = "".join(
        f'<div class="chip {"cur" if i + 1 == step else ("done" if i + 1 < step else "")}"><div class="n">{i + 1}</div>'
        f'<div class="z">{z}</div><div class="e">{e}</div></div>' for i, (z, e) in enumerate(steps))
    frac = step / len(steps)
    label = ("会话一 · 空记忆开始 / Session 1 · empty memory" if s == 1 else "会话二 · 新对话，同一份记忆 / Session 2 · same memory")
    return f'<div class="sess">{label}</div><div class="prog">{chips}</div><div class="bar"><i style="width:{frac*100:.0f}%"></i></div>'

def panel(d, speed=None):
    look = f'<div><div class="lab">看这里 / Look for</div><span class="look mono {d.get("tone","neutral")}">{E(d["look"])}</span></div>' if d.get("look") else ""
    sp = ("" if speed is None else
          f'<div class="spd"><span>{"原速 / real time" if speed <= 1.5 else "已加速 / sped up"}</span><b>{"×" + (str(speed).rstrip("0").rstrip(".") if speed != int(speed) else str(int(speed)))}</b></div>')
    note = f'<div class="note">{E(d["note"])}</div>' if d.get("note") else ""
    caps = "".join(f'<span class="capc">能力 {c} {CAP_NAME[c]}</span>' for c in CAP_OF[(d["s"], d["step"])])
    tech = TECH.get((d["s"], d["step"]))
    tech = f'<div class="tech mono"><b>技术细节 / for technical reviewers</b>{E(tech)}</div>' if tech else ""
    return f"""<div class="panel"><div class="brand"><span><b>Attest</b> × Claude 桌面应用 / desktop</span><span class="live">真实运行录屏 · LIVE RUN</span></div>
{progress(d["s"], d["step"])}<div class="caps">{caps}</div><div><h1>{E(d["title"][0])}</h1><h2>{E(d["title"][1])}</h2></div>
<div class="zh">{E(d["zh"])}</div><div class="en">{E(d["en"])}</div>{look}{note}{tech}{sp}</div>"""

def page(body): return f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"

def card_html(seg):
    c = seg["card"]
    if c == "intro":
        return page("""<div style="width:1920px;height:1080px;padding:120px 150px;display:flex;flex-direction:column;gap:34px">
<div class="brand" style="font-size:22px"><span><b>Attest</b></span><span class="live" style="font-size:18px">真实运行 · LIVE RUN</span></div>
<h1 style="font-size:60px">Attest × Claude 桌面应用：一次真实运行</h1><h2 style="font-size:32px">Attest in the Claude desktop app: a live run</h2>
<div class="zh" style="font-size:32px;max-width:1500px">AI 编程助手默认不记事：每次从零开始，评审纠正过的规矩，下一个任务还会再犯。Attest 给它一份团队的长期记忆：只记有证据的经验，挡住能通过测试的坏经验，拿不准的交给人。</div>
<div class="en" style="font-size:25px;max-width:1500px">AI coding assistants start from zero and repeat mistakes reviewers already fixed. Attest gives them a team memory: only evidenced lessons, no test-passing bad advice, and people decide what cannot be verified.</div>
<div style="display:flex;gap:18px;margin-top:auto;font-size:20px">
<span class="look neutral" style="font-size:19px">Claude Opus 5.5 + Attest MCP · Windows</span>
<span class="look hold" style="font-size:19px">合成仓库 ledgerly · 模拟评审与审批人 / synthetic repo, simulated reviewers</span>
<span class="look ok" style="font-size:19px">两次会话共用一份团队记忆 · 等待已加速 / two sessions, one memory, waits sped up</span></div></div>""")
    if c == "terms":
        rows = [("AI 编程助手（这里是 Claude）", "能自己读代码、改代码、运行测试的 AI 程序。", "An AI that reads, edits and tests code; here, Claude."),
                ("代码评审意见", "工程师对 AI 写的代码提出的修改意见；团队规矩大多藏在这里。（本演示为模拟）", "An engineer's change request; where team rules live (simulated here)."),
                ("测试", "自动检查代码是否做对的程序。通过测试，不等于每条建议都对。", "Automatic checks. Passing them does not prove every piece of advice right."),
                ("MCP 与 Attest 的两个工具", "MCP 是给 AI 装插件的通用接口。Recall：动手前查团队经验；Learn：做完后提交候选经验，由 Attest 审查。", "MCP plugs tools into an AI. Recall looks up team experience; Learn submits a candidate for Attest to check.")]
        body = "".join(f'<div class="box"><h3>{E(a)}</h3><p>{E(b)}</p><div class="e">{E(e)}</div></div>' for a, b, e in rows)
        return page(f"""<div class="card"><div class="sess" style="font-size:22px">看懂这段录像需要的四个词 / Four terms for this video</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">{body}</div>
<div class="note" style="font-size:17px;margin-top:auto">仓库 ledgerly 是合成的计费系统；评审意见与审批人是模拟的；AI 和 Attest 的每一步都是真实运行。/ Synthetic billing repo; simulated reviewers and approver; every agent and Attest step is a real run.</div></div>""")
    if c == "cap":
        zh, en, l1, l1e, why, whye, data, datae, how, howe = CAPS[seg["cap"]]
        box = lambda h, a, b: f'<div class="box"><h3>{h}</h3><p style="font-size:22px">{E(a)}</p><div class="e">{E(b)}</div></div>'
        return page(f"""<div class="card"><div class="sess" style="font-size:22px">能力 {seg["cap"]} · Capability {seg["cap"]}</div>
<h1 style="font-size:54px">{zh}</h1><h2 style="font-size:28px">{en}</h2>
<div class="zh" style="font-size:30px">{E(l1)}</div><div class="en" style="font-size:22px;margin-top:-14px">{E(l1e)}</div>
<div class="grid3">{box("为什么需要 · 传统做法的问题", why, whye)}{box("数据和依据从哪来", data, datae)}{box("Attest 怎么实现", how, howe)}</div></div>""")
    if c == "cf":
        return page("""<div class="card"><div class="sess" style="font-size:22px">补充说明 · 本次录像里没有运行的一项检查 / not run in this recording</div>
<h1 style="font-size:50px">反事实验证：测试通过，为什么还不够？</h1><h2 style="font-size:26px">Counterfactual verification: why passing tests is not enough</h2>
<div class="zh" style="font-size:28px">测试通过只说明代码整体没出错，不能说明是“这条经验”让测试通过：那处修改可能根本没被测试检查到。做法：把这条经验对应的修改撤掉，其他不变，再跑一次测试。撤掉后测试失败，才说明测试确实依赖它，计为一项硬证据。</div>
<div class="en" style="font-size:21px">Undo just that change and rerun the tests. Only if they then fail do the tests really vouch for the lesson.</div>
<div class="grid3">
<div class="box"><h3>真实例子 · 检验案例 T4</h3><p style="font-size:22px">任务 E04 的幂等修改：撤掉后，测试 <span class="mono">test_conv_c5_idempotent</span> 失败 → 计为硬证据。</p></div>
<div class="box"><h3>冻结的 15 个检验案例（事先标注）</h3><p style="font-size:22px">正确的经验 <b style="color:var(--ok)">7/8</b> 拿到这项证据；错误的 <b>0/4</b>、无法判断的 <b>0/2</b> 从没拿到。另 1 例因建议本身让测试失败被排除。</p></div>
<div class="box"><h3>本次桌面运行</h3><p style="font-size:22px">MCP 服务器不运行它（需要整套测试环境），用团队代码检查、登记编号和可信评审者原文代替。</p></div></div>
<div class="note" style="font-size:17px;margin-top:auto">真实实验回放 / recorded experiment：runs/counterfactual/report.md（attest/memory/counterfactual.py）</div></div>""")
    if c == "session2":
        return page("""<div style="width:1920px;height:1080px;padding:150px;display:flex;flex-direction:column;gap:30px;justify-content:center">
<div class="sess" style="font-size:26px">会话二 · 07:46，新对话 / Session 2 · 07:46, a new conversation</div>
<h1 style="font-size:56px">新对话，代码恢复到 v1.0.0，团队记忆保留</h1><h2 style="font-size:30px">A new conversation, code reset to v1.0.0, the team memory kept</h2>
<div class="zh" style="font-size:30px">带进来的：<span class="mono ok tag">at-0004 approved</span> 人批准的工单规则；<span class="mono bad tag">at-0002 retired</span> 人撤回的幂等规则；<span class="mono bad tag">at-0003 retired</span> 被拒的 float。</div>
<div class="en" style="font-size:24px">Carried in: the ticket rule a person approved, the idempotency rule a person retracted, the rejected float note.</div></div>""")
    if c == "results":
        return page("""<div style="width:1920px;height:1080px;padding:110px 150px;display:flex;flex-direction:column;gap:28px">
<h1 style="font-size:50px">一次录像证明机制能跑；效果看基准实验</h1><h2 style="font-size:28px">One run shows the mechanism works; the benchmark shows the effect</h2>
<div style="display:flex;gap:30px;margin-top:20px">
<div style="flex:1;background:var(--sheet);border:1px solid var(--rule);border-radius:14px;padding:34px">
<div class="lab" style="font-size:18px">D70 · 写入渠道攻击（合成，60 次）/ write-channel attacks (synthetic, 60)</div>
<div style="font-size:30px;font-weight:800;margin:14px 0">毒经验成为规则 / poison stored as a rule</div>
<table style="font-size:24px"><tr><td>Attest 门控 v4（与本次 MCP 同一套检查）</td><td class="mono" style="color:var(--ok);font-weight:800">0/60</td></tr>
<tr><td>无门槛 / no gate</td><td class="mono">46/60</td></tr><tr><td>预注册门槛 / preregistered gate</td><td class="mono">33/60</td></tr>
<tr><td>ACE-style</td><td class="mono">38/60</td></tr><tr><td>ReasoningBank-style</td><td class="mono">50/60</td></tr></table></div>
<div style="flex:1;background:var(--sheet);border:1px solid var(--rule);border-radius:14px;padding:34px">
<div class="lab" style="font-size:18px">D71 · 同一会话确认实验（探索性，55 次留出运行）/ exploratory, 55 held-out runs</div>
<div style="font-size:30px;font-weight:800;margin:14px 0">首次通过率与毒药使用 / pass@1 and poison applied</div>
<table style="font-size:24px"><tr><th></th><th>pass@1</th><th>用上毒药 / poison applied</th></tr>
<tr><td>门控 v4</td><td class="mono" style="color:var(--ok);font-weight:800">84%</td><td class="mono" style="color:var(--ok);font-weight:800">0/55</td></tr>
<tr><td>无门槛 / no gate</td><td class="mono">82%</td><td class="mono">13/55</td></tr>
<tr><td>ACE-style</td><td class="mono">65%</td><td class="mono">23/55</td></tr><tr><td>ReasoningBank-style</td><td class="mono">60%</td><td class="mono">28/55</td></tr></table>
<div class="note" style="font-size:16px;margin-top:12px">v4 对无门槛：+2% [−9%, +11%]，不更差（次要比较）/ v4 vs no gate: not worse (secondary)</div></div></div>
<div class="note" style="font-size:17px;margin-top:auto">来源 / sources: runs/poison_channels/report.md, runs/gate_confirm/report.md（仓库 tonglynn/ai-native-development-assessment）</div></div>""")
    if c == "end":
        return page("""<div class="card" style="justify-content:center;gap:30px">
<h1 style="font-size:50px">三项能力，一次真实运行</h1><h2 style="font-size:28px">Three capabilities in one live run</h2>
<div class="grid3">
<div class="box"><h3>能力 01</h3><p style="font-size:28px;font-weight:800">持续经验学习</p><div class="e">从评审纠正里学，新任务和新对话里自动用上。<br>Learns from reviews, reused on new tasks and sessions.</div></div>
<div class="box"><h3>能力 02</h3><p style="font-size:28px;font-weight:800">可信记忆与安全准入</p><div class="e">只收有证据的经验；能通过测试的坏经验被拦下，拿不准的挂起。<br>Evidence first; bad notes blocked, unclear ones held.</div></div>
<div class="box"><h3>能力 03</h3><p style="font-size:28px;font-weight:800">人工治理与全生命周期管理</p><div class="e">人批准、撤回，AI 做不了；每次变化都有记录。<br>People approve and retract; the AI cannot; everything is logged.</div></div></div>
<div class="note" style="font-size:17px">尚未实现：真实身份认证、MCP 路径上的反事实验证、不可篡改的审计存储。/ Not yet implemented: real authentication, counterfactual in MCP, tamper-proof audit storage.</div></div>""")
    d = dict(CARDS[c], s=seg["s"], step=seg["step"])
    if c == "ps":
        import base64
        uri = "data:image/png;base64," + base64.b64encode(Path("ps_crop.png").read_bytes()).decode()
        left = f'<div class="left"><div style="font-size:20px;font-weight:700;align-self:flex-start">PowerShell · .\\admin.bat review / approve</div><img src="{uri}" style="width:980px;border-radius:8px;box-shadow:0 2px 12px #0003"></div>'
    else:
        rows = "".join(f'<tr><td class="mono">{t}</td><td class="mono" style="white-space:nowrap"><b>{i}</b></td><td><span class="tag mono {k if k != "soft" else "neutral"}">{s}</span></td><td style="font-size:17px">{E(r)}</td></tr>'
                       for t, i, s, r, k in LOG_ROWS)
        left = f'<div class="left"><div style="font-size:20px;font-weight:700;align-self:flex-start">Attest 记忆日志 / memory log · ledgerly-demo</div><table><tr><th>时间</th><th>笔记</th><th>状态</th><th>记录 / reason</th></tr>{rows}</table></div>'
    return page(f'<div class="full">{left}{panel(d)}</div>')

def render_all():
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-proxy-server", "--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for i, seg in enumerate(SEG):
            if seg["kind"] == "card":
                pg.set_viewport_size({"width": 1920, "height": 1080}); pg.set_content(card_html(seg)); pg.wait_for_timeout(150)
                pg.screenshot(path=str(OUT / f"p{i:02d}.png"))
            else:
                pg.set_viewport_size({"width": 868, "height": 1080}); pg.set_content(page(panel(seg, seg["speed"]))); pg.wait_for_timeout(100)
                pg.screenshot(path=str(OUT / f"p{i:02d}.png"))
        b.close()

def compose():
    parts, cues, t = [], [], 0.0
    for i, seg in enumerate(SEG):
        out = OUT / f"s{i:02d}.mp4"
        if seg["kind"] == "card":
            dur = seg["dur"]
            cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", str(dur), "-framerate", "30", "-i", str(OUT / f"p{i:02d}.png"),
                   "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30", str(out)]
            d = CARDS.get(seg["card"])
            text = (d["zh"], d["en"]) if d else None
            if seg["card"] == "cap":
                k = CAPS[seg["cap"]]; text = (f"能力 {seg['cap']} {k[0]}：{k[2]}", f"Capability {seg['cap']} {k[1]}: {k[3]}")
            if seg["card"] == "terms":
                text = ("四个词：AI 编程助手、代码评审意见、测试，以及 Attest 的两个工具 Recall（动手前查经验）和 Learn（做完后提交候选经验）。",
                        "Four terms: the AI assistant, review comments, tests, and Attest's Recall and Learn tools.")
            if seg["card"] == "cf":
                text = ("反事实验证：撤掉这条经验对应的修改再跑测试，测试失败才说明测试依赖它。基准实验中运行，本次桌面运行没有运行。",
                        "Counterfactual check: undo the change and rerun the tests; run in the benchmark, not in this desktop run.")
            if seg["card"] == "intro":
                text = ("Attest 给 AI 编程助手一份团队的长期记忆：只记有证据的经验，挡住坏经验，拿不准的交给人。", "A team memory for AI coding assistants: evidence first, bad advice blocked, people decide the rest.")
        else:
            dur = (seg["b"] - seg["a"]) / seg["speed"]
            vf = (f"[0:v]setpts=(PTS-STARTPTS)/{seg['speed']},fps=30,scale=-2:1080,pad=1052:1080:(ow-iw)/2:0:color=0xe4e8e2[v];"
                  f"[v][1:v]hstack=inputs=2,format=yuv420p")
            cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(seg["a"]), "-t", str(seg["b"] - seg["a"]), "-i", SRC[seg["src"]],
                   "-loop", "1", "-i", str(OUT / f"p{i:02d}.png"), "-filter_complex", vf, "-t", f"{dur:.3f}", "-an",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30", str(out)]
            text = (seg["zh"], seg["en"])
        subprocess.run(cmd, check=True)
        real = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout)
        if text: cues.append((t, t + real, *text))
        t += real; parts.append(out)
    (OUT / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(OUT / "list.txt"), "-c", "copy", str(OUT / "film.mp4")], check=True)
    def ts(x): h, r = divmod(x, 3600); m, s = divmod(r, 60); return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"
    # merge consecutive cues with the same text
    merged = []
    for c in cues:
        if merged and merged[-1][2] == c[2]: merged[-1] = (merged[-1][0], c[1], c[2], c[3])
        else: merged.append(c)
    (OUT / "film.srt").write_text("".join(f"{k}\n{ts(a)} --> {ts(b)}\n{zh}\n{en}\n\n" for k, (a, b, zh, en) in enumerate(merged, 1)), encoding="utf-8")
    print("total", round(t, 1), "s;", len(merged), "cues")

if __name__ == "__main__":
    if "render" in sys.argv: render_all()
    if "compose" in sys.argv: compose()

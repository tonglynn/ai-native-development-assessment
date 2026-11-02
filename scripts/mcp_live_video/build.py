"""Render panels/cards with Playwright, compose segments with ffmpeg, concat, write SRT."""
import html, json, subprocess, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from plan import SEG, CARDS, LOG_ROWS, S1_STEPS, S2_STEPS, SRC

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
.chip .n{font-size:15px;font-weight:700}.chip .z{font-size:17px;font-weight:700}.chip .e{font-size:12px}
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
"""

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
    return f"""<div class="panel"><div class="brand"><span><b>Attest</b> × Claude 桌面应用 / desktop</span><span class="live">真实运行 · LIVE RUN</span></div>
{progress(d["s"], d["step"])}<div><h1>{E(d["title"][0])}</h1><h2>{E(d["title"][1])}</h2></div>
<div class="zh">{E(d["zh"])}</div><div class="en">{E(d["en"])}</div>{look}{note}{sp}</div>"""

def page(body): return f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"

def card_html(seg):
    c = seg["card"]
    if c == "intro":
        return page("""<div style="width:1920px;height:1080px;padding:120px 150px;display:flex;flex-direction:column;gap:34px">
<div class="brand" style="font-size:22px"><span><b>Attest</b></span><span class="live" style="font-size:18px">真实运行 · LIVE RUN</span></div>
<h1 style="font-size:60px">Attest × Claude 桌面应用：一次真实运行</h1><h2 style="font-size:32px">Attest in the Claude desktop app: a live run</h2>
<div class="zh" style="font-size:32px;max-width:1500px">编码 Agent 每次从零开始，评审纠正过的规矩下次还会再犯。Attest 让 Agent 只从被验证的经验里成长，挡住能通过测试的坏经验，并把拿不准的交给人。</div>
<div class="en" style="font-size:25px;max-width:1500px">Coding agents start from zero and repeat mistakes reviewers already fixed. Attest lets them grow only from verified experience, blocks bad advice that passes the tests, and hands what it cannot verify to people.</div>
<div style="display:flex;gap:18px;margin-top:auto;font-size:20px">
<span class="look neutral" style="font-size:19px">Claude Opus 5.5 + Attest MCP · Windows</span>
<span class="look hold" style="font-size:19px">合成仓库 ledgerly · 模拟评审与审批人 / synthetic repo, simulated reviewers</span>
<span class="look ok" style="font-size:19px">两次会话共用一份团队记忆 · 等待已加速 / two sessions, one memory, waits sped up</span></div></div>""")
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
        return page("""<div style="width:1920px;height:1080px;padding:150px;display:flex;flex-direction:column;gap:30px;justify-content:center">
<h1 style="font-size:58px">学得会，挡得住，人管得了</h1><h2 style="font-size:32px">Learns from verified reviews · blocks bad advice · people stay in charge</h2>
<div class="zh" style="font-size:28px">从评审纠正里学，只收有证据的经验；能通过测试的坏经验被代码检查拦下；拿不准的挂起等人；人一条命令就能批准或撤回，Agent 自己做不了。</div>
<div class="en" style="font-size:23px">Learns only evidenced lessons from reviews; a test-passing bad note is stopped by code checks; unverifiable notes wait for a person; people approve or retract with one command, agents cannot.</div></div>""")
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

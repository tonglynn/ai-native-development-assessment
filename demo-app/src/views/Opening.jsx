import { Button } from "../ui";
export default function Opening({ go }) {
  return (
    <div className="grid gap-7">
      <div className="grid gap-4">
        <h1 className="m-0 max-w-[20ch] text-[2.5rem] font-black leading-[1.1] tracking-tight">AI 编程助手不记得评审教过它什么。</h1>
        <p className="m-0 max-w-[60ch] text-lg text-soft">今天评审指出"重复的退款请求会退两次钱"，它改好了；下一个任务，它又犯同样的错。Attest 给它一份团队记忆：评审教过一次的经验，经过验证后记下来，下次自动用上；没有证据的、可能有害的，不让它记。</p>
      </div>
      <video className="w-full max-w-[920px] rounded-lg border border-rule bg-black" src="attest_film.mp4" controls muted playsInline preload="metadata" aria-label="Attest 是怎么工作的：84 秒动画" />
      <p className="m-0 -mt-4 text-xs text-soft">动画没有声音，画面上的文字即讲解；所有数字来自已提交的运行记录。</p>
      <div className="grid gap-2 text-sm text-soft">
        <p className="m-0">这个演示分三个场景。每个场景都基于已经提交的真实运行记录；需要现场判断的部分，在你的浏览器里运行 Attest 的真实代码。每处都标着它是<b className="text-ink">真实回放</b>、<b className="text-ink">现场运行</b>还是<b className="text-ink">模拟</b>。</p>
      </div>
      <div className="flex flex-wrap gap-3"><Button tone="primary" onClick={() => go("background")}>先看业务背景</Button><Button onClick={() => go("growth")}>直接看场景一</Button></div>
    </div>
  );
}

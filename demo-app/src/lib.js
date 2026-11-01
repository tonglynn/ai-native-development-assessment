import DATA from "./data.json";
export { DATA };
export const D = DATA.demo;
export const pct = x => `${Math.round(x * 100)}%`;
export const sysName = {
  attest_secure_v4: "Attest + 门控 v4", attest_secure_v31: "Attest + 门控 v3.1", attest: "Attest（预注册门槛）",
  attest_no_gate: "Attest 去掉门槛", ace: "ACE 式", reasoningbank: "ReasoningBank 式", attest_secure_v4_warm: "Attest + v4（使用中记忆）",
  no_memory: "不开记忆", attest_no_scope: "Attest 去掉作用域", attest_v4: "Attest + 门控 v4",
};
export const allNotes = () => {
  const m = new Map(D.memory_after_review.map(n => [n.id, n]));
  D.learn.forEach(l => l.new_notes.forEach(n => { if (!m.has(n.id)) m.set(n.id, n); }));
  return [...m.values()];
};
export const LABELS = [
  ["真实执行", "智能体运行、隐藏测试、经验提炼与门控审核（deepseek-flash；审核模型 deepseek-v4-pro）"],
  ["模拟", "评审意见（为基准编写）、业务负责人的决定（脚本）、演示用的新阈值笔记"],
  ["合成", "代码仓库 ledgerly 与毒评论"],
];

import { useState } from "react";
import { api, Prediction } from "../api";
import { Balls } from "../components/Balls";

const STRATEGIES = [
  { value: "adaptive", label: "自适应模型（在线学习 + 自校准）★ 推荐" },
  { value: "frequency_weighted", label: "频率加权（按历史频率随机）" },
  { value: "hot", label: "热号（历史出现最多）" },
  { value: "cold", label: "冷号（历史出现最少）" },
  { value: "balanced", label: "冷热均衡（3热+3冷）" },
  { value: "scarcity", label: "组合稀缺度（少出现的组合）" },
  { value: "random", label: "完全随机（基线对照）" },
];

export default function PredictPage() {
  const [count, setCount] = useState(5);
  const [strategy, setStrategy] = useState("adaptive");
  const [targetPeriod, setTargetPeriod] = useState("");
  const [notes, setNotes] = useState("");
  const [window, setWindow] = useState<string>("");
  const [result, setResult] = useState<Prediction | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onPredict(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      const r = await api.predict({
        count,
        strategy,
        target_period: targetPeriod || undefined,
        notes: notes || undefined,
        window: window ? parseInt(window, 10) : undefined,
      });
      setResult(r);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h1>生成预测</h1>
      <p className="muted">
        建议填写 <b>target_period</b>（要预测的下一期期号）。这样当你之后录入该期真实开奖时，
        系统会自动评估这批预测的命中情况。
      </p>

      <div className="card">
        <form onSubmit={onPredict} className="row">
          <label>预测组数
            <input type="number" min={1} max={100} value={count} onChange={(e) => setCount(parseInt(e.target.value, 10) || 1)} style={{ width: 80, marginLeft: 8 }} />
          </label>
          <label>策略
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)} style={{ marginLeft: 8 }}>
              {STRATEGIES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </label>
          <label>训练窗口（最近 N 期，留空=全部）
            <input value={window} onChange={(e) => setWindow(e.target.value)} placeholder="如 50" style={{ width: 80, marginLeft: 8 }} />
          </label>
          <label>目标期号
            <input value={targetPeriod} onChange={(e) => setTargetPeriod(e.target.value)} placeholder="如 2024002" style={{ marginLeft: 8 }} />
          </label>
          <label>备注
            <input value={notes} onChange={(e) => setNotes(e.target.value)} style={{ marginLeft: 8 }} />
          </label>
          <button disabled={loading}>{loading ? "生成中..." : "生成"}</button>
        </form>
      </div>

      {err && <div className="error">{err}</div>}

      {result && (
        <div className="card">
          <h3>预测 #{result.id} · 策略 {result.strategy} · 共 {result.items.length} 组</h3>
          <p className="muted">目标期：{result.target_period || "未指定"}</p>
          <table>
            <thead><tr><th>#</th><th>号码</th></tr></thead>
            <tbody>
              {result.items.map((it, i) => (
                <tr key={it.id}>
                  <td>{i + 1}</td>
                  <td><Balls reds={it.red_balls} blue={it.blue_ball} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

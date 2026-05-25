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
  const [mode, setMode] = useState<"predict" | "backtest">("predict");
  const [count, setCount] = useState(5);
  const [strategy, setStrategy] = useState("adaptive");
  const [targetPeriod, setTargetPeriod] = useState("");
  const [notes, setNotes] = useState("");
  const [win, setWin] = useState<string>("");
  const [result, setResult] = useState<Prediction | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onPredict(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setResult(null);
    setLoading(true);
    try {
      let r: Prediction;
      if (mode === "backtest") {
        if (!targetPeriod) throw new Error("回测必须填写目标期号");
        r = await api.backtest({
          target_period: targetPeriod,
          count,
          strategy,
          notes: notes || undefined,
        });
      } else {
        r = await api.predict({
          count,
          strategy,
          target_period: targetPeriod || undefined,
          notes: notes || undefined,
          window: win ? parseInt(win, 10) : undefined,
        });
      }
      setResult(r);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  const isBacktest = mode === "backtest";

  return (
    <>
      <h1>生成预测 / 回测</h1>

      <div className="card row">
        <label>
          <input
            type="radio" name="mode" checked={mode === "predict"}
            onChange={() => setMode("predict")}
          /> 正常预测
        </label>
        <label>
          <input
            type="radio" name="mode" checked={mode === "backtest"}
            onChange={() => setMode("backtest")}
          /> 回测（用目标期之前的数据预测，再与真实结果比较）
        </label>
      </div>

      <p className="muted">
        {isBacktest ? (
          <>
            <b>回测模式</b>：例如已录入 1-50 期，输入目标期号 <b>50</b>，系统会用第 1-49 期作为训练集，
            从零训练一个临时模型来预测第 50 期，然后立即用真实开奖评估。
            主模型状态不会被影响。结果会保存在历史里（标记为「回测」）。
          </>
        ) : (
          <>
            填写 <b>目标期号</b> 后，当你录入该期真实开奖时，系统会自动评估这批预测的命中情况。
          </>
        )}
      </p>

      <div className="card">
        <form onSubmit={onPredict} className="row">
          <label>预测组数
            <input type="number" min={1} max={100} value={count}
              onChange={(e) => setCount(parseInt(e.target.value, 10) || 1)}
              style={{ width: 80, marginLeft: 8 }} />
          </label>
          <label>策略
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)} style={{ marginLeft: 8 }}>
              {STRATEGIES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </label>
          {!isBacktest && (
            <label>训练窗口（最近 N 期，留空=全部）
              <input value={win} onChange={(e) => setWin(e.target.value)}
                placeholder="如 50" style={{ width: 80, marginLeft: 8 }} />
            </label>
          )}
          <label>{isBacktest ? "目标期号 *" : "目标期号"}
            <input value={targetPeriod} onChange={(e) => setTargetPeriod(e.target.value)}
              placeholder="如 2024050" style={{ marginLeft: 8 }} required={isBacktest} />
          </label>
          <label>备注
            <input value={notes} onChange={(e) => setNotes(e.target.value)} style={{ marginLeft: 8 }} />
          </label>
          <button disabled={loading}>
            {loading ? (isBacktest ? "回测中..." : "生成中...") : (isBacktest ? "回测" : "生成")}
          </button>
        </form>
      </div>

      {err && <div className="error">{err}</div>}

      {result && (
        <div className="card">
          <h3>
            预测 #{result.id} · 策略 {result.strategy} · 共 {result.items.length} 组
            {(result.notes ?? "").startsWith("[backtest]") && <span className="tag" style={{ marginLeft: 8 }}>回测</span>}
          </h3>
          <p className="muted">目标期：{result.target_period || "未指定"}</p>
          {isBacktest && result.items.some((it) => it.prize_level != null) && (
            <BacktestSummary items={result.items} />
          )}
          <table>
            <thead>
              <tr>
                <th>#</th><th>号码</th>
                {isBacktest && <><th>红命中</th><th>蓝命中</th><th>奖级</th></>}
              </tr>
            </thead>
            <tbody>
              {result.items.map((it, i) => (
                <tr key={it.id}>
                  <td>{i + 1}</td>
                  <td><Balls reds={it.red_balls} blue={it.blue_ball} /></td>
                  {isBacktest && (
                    <>
                      <td>{it.red_hits ?? "—"}</td>
                      <td>{it.blue_hit == null ? "—" : it.blue_hit ? "是" : "否"}</td>
                      <td>{prizeBadge(it.prize_level)}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function prizeBadge(level: number | null) {
  if (level == null) return "—";
  if (level === 0) return <span className="tag miss">未中</span>;
  const names = ["", "一等奖", "二等奖", "三等奖", "四等奖", "五等奖", "六等奖"];
  return <span className="tag prize">{names[level]}</span>;
}

function BacktestSummary({ items }: { items: Prediction["items"] }) {
  const evaluated = items.filter((i) => i.prize_level != null);
  const hits = evaluated.filter((i) => (i.prize_level ?? 0) > 0).length;
  const avgRedHits = evaluated.length === 0 ? 0
    : evaluated.reduce((s, i) => s + (i.red_hits ?? 0), 0) / evaluated.length;
  const blueHits = evaluated.filter((i) => i.blue_hit).length;
  return (
    <div className="card" style={{ background: "#f9fafb", boxShadow: "none" }}>
      <b>回测结果汇总</b>
      <div className="row" style={{ marginTop: 8 }}>
        <span className="tag">中奖 {hits} / {evaluated.length}</span>
        <span className="tag">平均红球命中 {avgRedHits.toFixed(2)} / 6</span>
        <span className="tag">蓝球命中 {blueHits} / {evaluated.length}</span>
      </div>
      <p className="muted" style={{ marginTop: 8 }}>
        参考：完全均匀随机时，6 红球期望命中 ≈ 6 × 6/33 ≈ 1.09，蓝球期望命中率 = 1/16 ≈ 6.25%
      </p>
    </div>
  );
}

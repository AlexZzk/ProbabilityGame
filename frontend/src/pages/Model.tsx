import { useEffect, useState } from "react";
import { api, ModelEvent, ModelState } from "../api";

const RED_N = 33;
const BLUE_N = 16;

export default function ModelPage() {
  const [state, setState] = useState<ModelState | null>(null);
  const [events, setEvents] = useState<ModelEvent[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload() {
    setErr(null);
    try {
      const [s, e] = await Promise.all([api.modelState(), api.modelEvents()]);
      setState(s);
      setEvents(e);
    } catch (ex) {
      setErr(String(ex));
    }
  }

  useEffect(() => { reload(); }, []);

  async function onTrain(full: boolean) {
    setBusy(true); setMsg(null); setErr(null);
    try {
      const r = await api.modelTrain(full);
      setMsg(`训练完成：${full ? "全量重训" : "增量"} ${r.trained} 期，触发 ${r.calibrated} 次校准，模型版本 → ${r.version}`);
      await reload();
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  }

  async function onReset() {
    if (!confirm("将模型重置为公平先验（uniform）？历史训练日志保留。")) return;
    setBusy(true); setMsg(null); setErr(null);
    try {
      await api.modelReset();
      setMsg("模型已重置");
      await reload();
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  }

  const trainEvents = events.filter((e) => e.event_type === "train");
  const calEvents = events.filter((e) => e.event_type === "calibrate");

  return (
    <>
      <h1>预测模型</h1>
      <p className="muted">
        自适应 Dirichlet-Multinomial 模型。每录入一期真实开奖会自动训练；每 5 步触发一次自校准，
        模型会比较「最近经验分布」与「自身预测分布」的 KL 距离，自动调整温度 T。
        详细推导见 <a href="https://github.com/AlexZzk/ProbabilityGame/blob/main/docs/MODEL.md" target="_blank" rel="noreferrer">docs/MODEL.md</a>。
      </p>

      {msg && <div className="success">{msg}</div>}
      {err && <div className="error">{err}</div>}

      <div className="card row">
        <button disabled={busy} onClick={() => onTrain(false)}>对未训练数据增量训练</button>
        <button disabled={busy} className="secondary" onClick={() => onTrain(true)}>全量重训</button>
        <button disabled={busy} className="secondary" onClick={onReset}>重置为公平先验</button>
      </div>

      {state && (
        <>
          <div className="card">
            <h3>当前模型状态</h3>
            <table>
              <tbody>
                <tr><th>版本（训练步数）</th><td>{state.version}</td></tr>
                <tr><th>温度 T</th><td>{state.temperature.toFixed(4)} <span className="muted">（1.0 = 后验，&gt;1 偏均匀，&lt;1 偏尖锐）</span></td></tr>
                <tr><th>学习率 η</th><td>{state.learning_rate}</td></tr>
                <tr><th>衰减系数</th><td>{state.decay}</td></tr>
                <tr><th>先验强度 α₀</th><td>{state.prior_strength}</td></tr>
                <tr><th>已训练到的 draw_id</th><td>{state.last_trained_draw_id ?? "—"}</td></tr>
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3>红球概率分布（模型 vs 均匀 1/33 = {(1/RED_N).toFixed(4)}）</h3>
            <ProbBars probs={state.red_probs} uniform={1 / RED_N} cols={11} />
          </div>

          <div className="card">
            <h3>蓝球概率分布（模型 vs 均匀 1/16 = {(1/BLUE_N).toFixed(4)}）</h3>
            <ProbBars probs={state.blue_probs} uniform={1 / BLUE_N} cols={8} />
          </div>

          <div className="card">
            <h3>训练损失 NLL（越低说明模型对真实开奖越「不意外」）</h3>
            <SparkLine values={trainEvents.map((e) => e.nll ?? 0)} />
            <p className="muted">共 {trainEvents.length} 步</p>
          </div>

          <div className="card">
            <h3>自校准事件</h3>
            <p className="muted">每次校准都比较「经验分布 vs 模型」和「经验分布 vs 均匀」的 KL 散度</p>
            <table>
              <thead>
                <tr><th>#</th><th>时间</th><th>KL(经验‖模型)</th><th>KL(经验‖均匀)</th><th>决策</th><th>T 变化</th></tr>
              </thead>
              <tbody>
                {calEvents.slice(-20).reverse().map((e) => {
                  const kModel = (e.kl_red_vs_model ?? 0) + (e.kl_blue_vs_model ?? 0);
                  const kUnif = (e.kl_red_vs_uniform ?? 0) + (e.kl_blue_vs_uniform ?? 0);
                  return (
                    <tr key={e.id}>
                      <td>v{e.version}</td>
                      <td>{new Date(e.created_at).toLocaleString()}</td>
                      <td>{kModel.toFixed(4)}</td>
                      <td>{kUnif.toFixed(4)}</td>
                      <td>
                        {e.decision === "raise" && <span className="tag">升温（回退均匀）</span>}
                        {e.decision === "lower" && <span className="tag prize">降温（更尖锐）</span>}
                        {e.decision === "keep" && <span className="tag miss">保持</span>}
                      </td>
                      <td>{(e.temperature_before ?? 0).toFixed(3)} → {(e.temperature_after ?? 0).toFixed(3)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}

function ProbBars({ probs, uniform, cols }: { probs: number[]; uniform: number; cols: number }) {
  const max = Math.max(uniform, ...probs);
  return (
    <div style={{ display: "grid", gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 6 }}>
      {probs.map((p, i) => {
        const pPct = Math.max(2, Math.round((p / max) * 100));
        const uPct = Math.max(2, Math.round((uniform / max) * 100));
        return (
          <div key={i} className="cell">
            <div><b>{i + 1}</b></div>
            <div style={{ position: "relative", height: 8, background: "#f3f4f6", borderRadius: 4, marginTop: 4 }}>
              <div style={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${pPct}%`, background: p > uniform ? "#ef4444" : "#3b82f6", borderRadius: 4 }} />
              <div style={{ position: "absolute", left: `${uPct}%`, top: -2, height: 12, width: 1, background: "#111" }} title="uniform baseline" />
            </div>
            <div className="muted">{(p * 100).toFixed(2)}%</div>
          </div>
        );
      })}
    </div>
  );
}

function SparkLine({ values }: { values: number[] }) {
  if (values.length === 0) return <p className="muted">暂无数据</p>;
  const w = 600, h = 80, pad = 4;
  const min = Math.min(...values), max = Math.max(...values);
  const norm = (v: number) => max === min ? h / 2 : pad + (h - 2 * pad) * (1 - (v - min) / (max - min));
  const step = (w - 2 * pad) / Math.max(1, values.length - 1);
  const d = values.map((v, i) => `${i === 0 ? "M" : "L"} ${pad + i * step} ${norm(v)}`).join(" ");
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{ background: "#f9fafb", borderRadius: 6 }}>
      <path d={d} stroke="#2563eb" strokeWidth={1.5} fill="none" />
      <text x={pad} y={12} fontSize="10" fill="#6b7280">{max.toFixed(2)}</text>
      <text x={pad} y={h - 2} fontSize="10" fill="#6b7280">{min.toFixed(2)}</text>
    </svg>
  );
}

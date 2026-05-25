import { useEffect, useMemo, useState } from "react";
import { AggregateResponse, AggregatedItem, Prediction, api } from "../api";
import { Balls } from "../components/Balls";

export default function AggregatePage() {
  const [preds, setPreds] = useState<Prediction[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [targetPeriod, setTargetPeriod] = useState("");
  const [strategy, setStrategy] = useState("");
  const [topK, setTopK] = useState(10);
  const [method, setMethod] = useState<"consensus" | "resample">("consensus");
  const [result, setResult] = useState<AggregateResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.listPredictions().then(setPreds).catch((e) => setErr(String(e)));
  }, []);

  const visible = useMemo(() => {
    return preds.filter((p) => {
      if (targetPeriod && (p.target_period ?? "") !== targetPeriod) return false;
      if (strategy && p.strategy !== strategy) return false;
      return true;
    });
  }, [preds, targetPeriod, strategy]);

  function toggle(id: number) {
    const s = new Set(selected);
    s.has(id) ? s.delete(id) : s.add(id);
    setSelected(s);
  }
  function selectAll() { setSelected(new Set(visible.map((p) => p.id))); }
  function clearSel() { setSelected(new Set()); }

  async function run() {
    setErr(null); setResult(null); setLoading(true);
    try {
      const r = await api.aggregatePredictions({
        prediction_ids: selected.size > 0 ? Array.from(selected) : undefined,
        target_period: selected.size === 0 && targetPeriod ? targetPeriod : undefined,
        strategy: selected.size === 0 && strategy ? strategy : undefined,
        top_k: topK,
        method,
      });
      setResult(r);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  const sourceItems = selected.size > 0
    ? visible.filter((p) => selected.has(p.id)).reduce((s, p) => s + p.items.length, 0)
    : visible.reduce((s, p) => s + p.items.length, 0);

  return (
    <>
      <h1>聚合选号（Ensemble）</h1>
      <p className="muted">
        从多次预测里挑出共识最强的 K 注。这是 ML 里的投票/bagging 思路，能减少单次预测的方差；
        <b>但不会改变期望回报率</b>——它只是帮你用有限预算覆盖多次预测的「共识」。
      </p>

      <div className="card">
        <h3>① 选择要参与聚合的预测</h3>
        <div className="row" style={{ marginBottom: 8 }}>
          <label>按目标期号过滤
            <input value={targetPeriod} onChange={(e) => setTargetPeriod(e.target.value)}
              placeholder="如 2026058" style={{ marginLeft: 8 }} />
          </label>
          <label>按策略过滤
            <input value={strategy} onChange={(e) => setStrategy(e.target.value)}
              placeholder="如 adaptive" style={{ marginLeft: 8 }} />
          </label>
          <button className="secondary" onClick={selectAll}>全选可见</button>
          <button className="secondary" onClick={clearSel}>清空</button>
          <span className="muted">
            已选 {selected.size} 条 / 共 {visible.length} 条 (可见) → 候选组合约 {sourceItems}
          </span>
        </div>
        <p className="muted">
          提示：勾选具体预测时，会忽略上面的过滤器；不勾选时则用过滤条件聚合所有匹配的预测。
        </p>
        <table>
          <thead>
            <tr>
              <th style={{ width: 40 }}></th>
              <th>#</th><th>策略</th><th>目标期</th><th>组数</th><th>命中</th><th>备注</th><th>时间</th>
            </tr>
          </thead>
          <tbody>
            {visible.slice(0, 100).map((p) => {
              const evaluated = p.items.filter((i) => i.prize_level != null);
              const hits = evaluated.filter((i) => (i.prize_level ?? 0) > 0).length;
              return (
                <tr key={p.id}>
                  <td><input type="checkbox" checked={selected.has(p.id)} onChange={() => toggle(p.id)} /></td>
                  <td>{p.id}</td>
                  <td>{p.strategy}</td>
                  <td>{p.target_period ?? "—"}</td>
                  <td>{p.items.length}</td>
                  <td>{evaluated.length > 0 ? `${hits}/${evaluated.length}` : "—"}</td>
                  <td>{p.notes ?? ""}</td>
                  <td className="muted">{new Date(p.created_at).toLocaleString()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="card row">
        <label>聚合方法
          <select value={method} onChange={(e) => setMethod(e.target.value as "consensus" | "resample")}
            style={{ marginLeft: 8 }}>
            <option value="consensus">consensus：从候选中挑共识最高的 K 注</option>
            <option value="resample">resample：按投票频率重新采样 K 注新组合</option>
          </select>
        </label>
        <label>top K
          <input type="number" min={1} max={100} value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value, 10) || 1)}
            style={{ width: 80, marginLeft: 8 }} />
        </label>
        <button onClick={run} disabled={loading || (selected.size === 0 && !targetPeriod && !strategy)}>
          {loading ? "聚合中..." : "执行聚合"}
        </button>
      </div>

      {err && <div className="error">{err}</div>}

      {result && <AggregateResult res={result} />}
    </>
  );
}

function AggregateResult({ res }: { res: AggregateResponse }) {
  const redArr = Array.from({ length: 33 }, (_, i) => res.red_votes[String(i + 1)] ?? 0);
  const blueArr = Array.from({ length: 16 }, (_, i) => res.blue_votes[String(i + 1)] ?? 0);
  const redMax = Math.max(1, ...redArr);
  const blueMax = Math.max(1, ...blueArr);

  return (
    <>
      <div className="card">
        <h3>聚合结果（{res.method}）</h3>
        <p className="muted">
          源自 {res.source_predictions} 次预测、共 {res.source_items} 组号码。
        </p>
      </div>

      <div className="card">
        <h3>红球投票分布</h3>
        <VoteBars values={redArr} max={redMax} cols={11} />
      </div>

      <div className="card">
        <h3>蓝球投票分布</h3>
        <VoteBars values={blueArr} max={blueMax} cols={8} />
      </div>

      <div className="card">
        <h3>最终选出的 {res.selected.length} 注</h3>
        <table>
          <thead><tr><th>#</th><th>号码</th><th>共识分</th></tr></thead>
          <tbody>
            {res.selected.map((it: AggregatedItem, i: number) => (
              <tr key={i}>
                <td>{i + 1}</td>
                <td><Balls reds={it.red_balls} blue={it.blue_ball} /></td>
                <td>{it.score.toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function VoteBars({ values, max, cols }: { values: number[]; max: number; cols: number }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 6 }}>
      {values.map((v, i) => {
        const pct = Math.max(2, Math.round((v / max) * 100));
        return (
          <div key={i} className="cell">
            <div><b>{i + 1}</b></div>
            <div style={{ height: 8, background: "#f3f4f6", borderRadius: 4, marginTop: 4 }}>
              <div style={{ height: "100%", width: `${pct}%`, background: "#2563eb", borderRadius: 4 }} />
            </div>
            <div className="muted">{v}</div>
          </div>
        );
      })}
    </div>
  );
}

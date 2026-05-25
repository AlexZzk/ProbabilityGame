import { useEffect, useState } from "react";
import { api, FrequencyStats } from "../api";

export default function FrequencyPage() {
  const [stats, setStats] = useState<FrequencyStats | null>(null);
  const [window, setWindow] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setErr(null);
    try {
      const w = window ? parseInt(window, 10) : undefined;
      setStats(await api.frequency(w));
    } catch (e) {
      setErr(String(e));
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  function bar(value: number, max: number) {
    const pct = max ? Math.max(2, Math.round((value / max) * 100)) : 0;
    return <div className="freq-bar" style={{ width: `${pct}%` }} />;
  }

  const redMax = stats ? Math.max(0, ...Object.values(stats.red)) : 0;
  const blueMax = stats ? Math.max(0, ...Object.values(stats.blue)) : 0;

  return (
    <>
      <h1>历史频率统计</h1>
      <div className="card row">
        <label>仅统计最近 N 期（留空=全部）
          <input value={window} onChange={(e) => setWindow(e.target.value)} placeholder="例如 50" style={{ marginLeft: 8 }} />
        </label>
        <button onClick={load}>刷新</button>
        <span className="muted">共统计 {stats?.total_draws ?? 0} 期</span>
      </div>
      {err && <div className="error">{err}</div>}

      {stats && (
        <>
          <div className="card">
            <h3>红球 1-33</h3>
            <div className="grid-33">
              {Object.entries(stats.red).map(([n, v]) => (
                <div className="cell" key={n}>
                  <div><b>{n}</b></div>
                  <div>{bar(v, redMax)}</div>
                  <div className="muted">{v}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <h3>蓝球 1-16</h3>
            <div className="grid-16">
              {Object.entries(stats.blue).map(([n, v]) => (
                <div className="cell" key={n}>
                  <div><b>{n}</b></div>
                  <div>{bar(v, blueMax)}</div>
                  <div className="muted">{v}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </>
  );
}

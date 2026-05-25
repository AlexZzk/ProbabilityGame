import { useEffect, useState } from "react";
import { api, Draw } from "../api";
import { Balls } from "../components/Balls";

export default function DrawsPage() {
  const [draws, setDraws] = useState<Draw[]>([]);
  const [total, setTotal] = useState(0);
  const [period, setPeriod] = useState("");
  const [reds, setReds] = useState("");
  const [blue, setBlue] = useState("");
  const [drawDate, setDrawDate] = useState("");
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  async function reload() {
    const [list, c] = await Promise.all([api.listDraws(), api.countDraws()]);
    setDraws(list);
    setTotal(c.total);
  }

  useEffect(() => {
    reload().catch((e) => setMsg({ type: "err", text: String(e) }));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      const redArr = reds
        .split(/[\s,，、]+/)
        .filter(Boolean)
        .map((n) => parseInt(n, 10));
      await api.createDraw({
        period,
        red_balls: redArr,
        blue_ball: parseInt(blue, 10),
        draw_date: drawDate ? new Date(drawDate).toISOString() : null,
      });
      setMsg({ type: "ok", text: `已录入 ${period}，并对该期已有预测自动评估完成。` });
      setPeriod(""); setReds(""); setBlue(""); setDrawDate("");
      await reload();
    } catch (e) {
      setMsg({ type: "err", text: String(e) });
    }
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setMsg(null);
    try {
      const r = await api.uploadCsv(file);
      setMsg({ type: "ok", text: `CSV 已导入/更新 ${r.inserted_or_updated} 条` });
      await reload();
    } catch (err) {
      setMsg({ type: "err", text: String(err) });
    } finally {
      e.target.value = "";
    }
  }

  return (
    <>
      <h1>训练集（开奖历史）</h1>
      <p className="muted">当前共 {total} 期。新录入一期真实开奖时，会自动对 target_period 等于该期的预测进行评估。</p>

      {msg && <div className={msg.type === "ok" ? "success" : "error"}>{msg.text}</div>}

      <div className="card">
        <h3>录入单期</h3>
        <form onSubmit={onSubmit} className="row">
          <input placeholder="期号（如 2024001）" value={period} onChange={(e) => setPeriod(e.target.value)} required />
          <input placeholder="6 个红球 用空格或逗号" value={reds} onChange={(e) => setReds(e.target.value)} required style={{ flex: 1, minWidth: 220 }} />
          <input placeholder="蓝球" value={blue} onChange={(e) => setBlue(e.target.value)} required style={{ width: 80 }} />
          <input type="date" value={drawDate} onChange={(e) => setDrawDate(e.target.value)} />
          <button type="submit">录入 / 更新</button>
        </form>
      </div>

      <div className="card">
        <h3>批量上传 CSV</h3>
        <p className="muted">列顺序：period, red1, red2, red3, red4, red5, red6, blue, draw_date(可选)</p>
        <input type="file" accept=".csv,text/csv" onChange={onUpload} />
      </div>

      <div className="card">
        <h3>最近 {draws.length} 期</h3>
        <table>
          <thead>
            <tr><th>期号</th><th>开奖号码</th><th>开奖日期</th></tr>
          </thead>
          <tbody>
            {draws.map((d) => (
              <tr key={d.id}>
                <td>{d.period}</td>
                <td><Balls reds={d.red_balls} blue={d.blue_ball} /></td>
                <td>{d.draw_date ? d.draw_date.slice(0, 10) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

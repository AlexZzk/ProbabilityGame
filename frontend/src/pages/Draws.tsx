import { useEffect, useState } from "react";
import { api, Draw } from "../api";
import { Balls } from "../components/Balls";

interface FormState {
  id: number | null;  // null = 新建; number = 编辑
  period: string;
  reds: string;
  blue: string;
  drawDate: string;
}

const EMPTY: FormState = { id: null, period: "", reds: "", blue: "", drawDate: "" };

export default function DrawsPage() {
  const [draws, setDraws] = useState<Draw[]>([]);
  const [total, setTotal] = useState(0);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  async function reload() {
    const [list, c] = await Promise.all([api.listDraws(), api.countDraws()]);
    setDraws(list);
    setTotal(c.total);
  }

  useEffect(() => {
    reload().catch((e) => setMsg({ type: "err", text: String(e) }));
  }, []);

  function startEdit(d: Draw) {
    setForm({
      id: d.id,
      period: d.period,
      reds: d.red_balls.join(" "),
      blue: String(d.blue_ball),
      drawDate: d.draw_date ? d.draw_date.slice(0, 10) : "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEdit() { setForm(EMPTY); }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      const redArr = form.reds
        .split(/[\s,，、]+/).filter(Boolean).map((n) => parseInt(n, 10));
      const payload = {
        period: form.period,
        red_balls: redArr,
        blue_ball: parseInt(form.blue, 10),
        draw_date: form.drawDate ? new Date(form.drawDate).toISOString() : null,
      };
      if (form.id) {
        await api.updateDraw(form.id, payload);
        setMsg({ type: "ok", text: `已更新 ${form.period}。该期已有预测自动重新评估；预测模型已自动全量重训。` });
      } else {
        await api.createDraw(payload);
        setMsg({ type: "ok", text: `已录入 ${form.period}，并对该期已有预测自动评估完成。` });
      }
      setForm(EMPTY);
      await reload();
    } catch (e) {
      setMsg({ type: "err", text: String(e) });
    }
  }

  async function onDelete(d: Draw) {
    if (!confirm(`确认删除期号 ${d.period}？\n该期相关预测的评估会被清除，预测模型将全量重训。`)) return;
    setMsg(null);
    try {
      await api.deleteDraw(d.id);
      setMsg({ type: "ok", text: `已删除 ${d.period}` });
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
      <p className="muted">
        当前共 {total} 期。每条记录都可以修改 / 删除——这些操作会自动重新评估该期相关预测，
        并触发模型全量重训以保证状态一致。
      </p>

      {msg && <div className={msg.type === "ok" ? "success" : "error"}>{msg.text}</div>}

      <div className="card">
        <h3>{form.id ? `编辑 #${form.id}` : "录入单期"}</h3>
        <form onSubmit={onSubmit} className="row">
          <input placeholder="期号（如 2024001）" value={form.period}
            onChange={(e) => setForm({ ...form, period: e.target.value })} required />
          <input placeholder="6 个红球 用空格或逗号" value={form.reds}
            onChange={(e) => setForm({ ...form, reds: e.target.value })}
            required style={{ flex: 1, minWidth: 220 }} />
          <input placeholder="蓝球" value={form.blue}
            onChange={(e) => setForm({ ...form, blue: e.target.value })}
            required style={{ width: 80 }} />
          <input type="date" value={form.drawDate}
            onChange={(e) => setForm({ ...form, drawDate: e.target.value })} />
          <button type="submit">{form.id ? "保存修改" : "录入"}</button>
          {form.id && <button type="button" className="secondary" onClick={cancelEdit}>取消</button>}
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
            <tr><th>期号</th><th>开奖号码</th><th>开奖日期</th><th style={{ width: 160 }}>操作</th></tr>
          </thead>
          <tbody>
            {draws.map((d) => (
              <tr key={d.id}>
                <td>{d.period}</td>
                <td><Balls reds={d.red_balls} blue={d.blue_ball} /></td>
                <td>{d.draw_date ? d.draw_date.slice(0, 10) : "—"}</td>
                <td>
                  <button className="secondary" onClick={() => startEdit(d)} style={{ marginRight: 6 }}>编辑</button>
                  <button className="secondary" onClick={() => onDelete(d)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

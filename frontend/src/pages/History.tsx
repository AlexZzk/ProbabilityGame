import { useEffect, useState } from "react";
import { api, Prediction } from "../api";
import { Balls } from "../components/Balls";

function prizeTag(level: number | null) {
  if (level == null) return <span className="tag muted">未评估</span>;
  if (level === 0) return <span className="tag miss">未中</span>;
  const names = ["", "一等奖", "二等奖", "三等奖", "四等奖", "五等奖", "六等奖"];
  return <span className="tag prize">{names[level]}</span>;
}

export default function HistoryPage() {
  const [list, setList] = useState<Prediction[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.listPredictions().then(setList).catch((e) => setErr(String(e)));
  }, []);

  return (
    <>
      <h1>历史预测与评估</h1>
      <p className="muted">每条预测的命中情况会在你录入对应期号的真实开奖时自动回填。</p>
      {err && <div className="error">{err}</div>}

      {list.map((p) => {
        const evaluated = p.items.filter((i) => i.prize_level != null);
        const hit = evaluated.filter((i) => (i.prize_level ?? 0) > 0).length;
        return (
          <div className="card" key={p.id}>
            <h3>
              #{p.id} · {p.strategy} · 目标期 {p.target_period || "—"} ·{" "}
              <span className="muted" style={{ fontWeight: "normal" }}>
                {new Date(p.created_at).toLocaleString()}
              </span>
            </h3>
            {evaluated.length > 0 && (
              <p className="muted">
                已评估 {evaluated.length}/{p.items.length} 组，中奖 {hit} 组
              </p>
            )}
            <table>
              <thead>
                <tr><th>#</th><th>号码</th><th>红命中</th><th>蓝命中</th><th>奖级</th></tr>
              </thead>
              <tbody>
                {p.items.map((it, i) => (
                  <tr key={it.id}>
                    <td>{i + 1}</td>
                    <td><Balls reds={it.red_balls} blue={it.blue_ball} /></td>
                    <td>{it.red_hits ?? "—"}</td>
                    <td>{it.blue_hit == null ? "—" : it.blue_hit ? "是" : "否"}</td>
                    <td>{prizeTag(it.prize_level)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
    </>
  );
}

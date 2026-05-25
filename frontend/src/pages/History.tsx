import { useEffect, useMemo, useState } from "react";
import { api, HistoryGroup, Prediction, PredictionItem } from "../api";
import { Balls } from "../components/Balls";

function prizeTag(level: number | null) {
  if (level == null) return <span className="tag miss">未评估</span>;
  if (level === 0) return <span className="tag miss">未中</span>;
  const names = ["", "一等奖", "二等奖", "三等奖", "四等奖", "五等奖", "六等奖"];
  return <span className="tag prize">{names[level]}</span>;
}

export default function HistoryPage() {
  const [groups, setGroups] = useState<HistoryGroup[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [openPeriods, setOpenPeriods] = useState<Set<string>>(new Set());
  const [openPreds, setOpenPreds] = useState<Set<number>>(new Set());
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api.history().then(setGroups).catch((e) => setErr(String(e)));
  }, []);

  function togglePeriod(p: string) {
    const s = new Set(openPeriods);
    s.has(p) ? s.delete(p) : s.add(p);
    setOpenPeriods(s);
  }
  function togglePred(id: number) {
    const s = new Set(openPreds);
    s.has(id) ? s.delete(id) : s.add(id);
    setOpenPreds(s);
  }

  const filtered = useMemo(() => {
    if (!filter) return groups;
    return groups.filter((g) => (g.target_period ?? "未指定").includes(filter));
  }, [groups, filter]);

  return (
    <>
      <h1>历史与评估</h1>
      <p className="muted">
        按目标期号分组。每组展示该期真实开奖（如已录入）和所有相关预测。点击期号展开预测列表；点击预测展开号码明细。
      </p>

      <div className="card row">
        <input placeholder="按期号过滤" value={filter} onChange={(e) => setFilter(e.target.value)} />
        <span className="muted">共 {groups.length} 组</span>
      </div>

      {err && <div className="error">{err}</div>}

      {filtered.map((g) => {
        const periodKey = g.target_period ?? "__none__";
        const isOpen = openPeriods.has(periodKey);
        return (
          <div className="card" key={periodKey}>
            <div
              style={{ display: "flex", alignItems: "center", justifyContent: "space-between", cursor: "pointer" }}
              onClick={() => togglePeriod(periodKey)}
            >
              <div>
                <h3 style={{ margin: 0 }}>
                  <span style={{ display: "inline-block", width: 16 }}>{isOpen ? "▾" : "▸"}</span>
                  {g.target_period ?? "（未指定期号）"}
                </h3>
                <div className="muted" style={{ marginTop: 4 }}>
                  {g.draw
                    ? <>真实开奖：<Balls reds={g.draw.red_balls} blue={g.draw.blue_ball} /></>
                    : <>真实开奖：<span className="tag miss">未录入</span></>}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div>
                  <span className="tag">{g.prediction_count} 次预测</span>{" "}
                  <span className="tag">{g.item_count} 组号码</span>
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {g.evaluated_count > 0
                    ? `已评估 ${g.evaluated_count}/${g.item_count}，中奖 ${g.hit_count}`
                    : "等待真实开奖录入后评估"}
                </div>
              </div>
            </div>

            {isOpen && (
              <div style={{ marginTop: 16, borderTop: "1px solid #eee", paddingTop: 12 }}>
                {g.predictions.map((p) => (
                  <PredictionRow
                    key={p.id}
                    pred={p}
                    realReds={g.draw?.red_balls}
                    realBlue={g.draw?.blue_ball}
                    open={openPreds.has(p.id)}
                    onToggle={() => togglePred(p.id)}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </>
  );
}

function PredictionRow({
  pred,
  realReds,
  realBlue,
  open,
  onToggle,
}: {
  pred: Prediction;
  realReds: number[] | undefined;
  realBlue: number | undefined;
  open: boolean;
  onToggle: () => void;
}) {
  const evaluated = pred.items.filter((i) => i.prize_level != null);
  const hits = evaluated.filter((i) => (i.prize_level ?? 0) > 0).length;
  const isBacktest = (pred.notes ?? "").startsWith("[backtest]");
  return (
    <div style={{ padding: "8px 0", borderBottom: "1px solid #f3f4f6" }}>
      <div
        style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
        onClick={onToggle}
      >
        <div>
          <b>#{pred.id}</b> {" · "}
          <span className="muted">{pred.strategy}</span>
          {isBacktest && <span className="tag" style={{ marginLeft: 6 }}>回测</span>}
          {pred.notes && !isBacktest && <span className="muted" style={{ marginLeft: 6 }}>{pred.notes}</span>}
        </div>
        <div className="muted">
          {pred.items.length} 组
          {evaluated.length > 0 && ` · 中 ${hits}`}
          {" · "}
          {new Date(pred.created_at).toLocaleString()}
          <span style={{ marginLeft: 8 }}>{open ? "▾" : "▸"}</span>
        </div>
      </div>
      {open && (
        <table style={{ marginTop: 8 }}>
          <thead>
            <tr><th>#</th><th>号码</th><th>红命中</th><th>蓝命中</th><th>奖级</th></tr>
          </thead>
          <tbody>
            {pred.items.map((it, i) => (
              <ItemRow key={it.id} idx={i} item={it} realReds={realReds} realBlue={realBlue} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function ItemRow({
  idx, item, realReds, realBlue,
}: { idx: number; item: PredictionItem; realReds?: number[]; realBlue?: number }) {
  const hl = realReds ? new Set(item.red_balls.filter((n) => realReds.includes(n))) : undefined;
  const hlBlue = realBlue !== undefined && item.blue_ball === realBlue;
  return (
    <tr>
      <td>{idx + 1}</td>
      <td><Balls reds={item.red_balls} blue={item.blue_ball} highlightReds={hl} highlightBlue={hlBlue} /></td>
      <td>{item.red_hits ?? "—"}</td>
      <td>{item.blue_hit == null ? "—" : item.blue_hit ? "是" : "否"}</td>
      <td>{prizeTag(item.prize_level)}</td>
    </tr>
  );
}

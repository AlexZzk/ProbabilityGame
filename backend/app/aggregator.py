"""把多组预测聚合成最终 K 组——ensemble / voting 思路。

输入：一批已有的 PredictionItem（来自任意数量的 Prediction 对象）
输出：top_k 个组合 + 每个号码的投票频次（便于解释）

两种方法：
  - "consensus"：直接从输入候选里挑「与众多预测重合度最高」的 K 组
  - "resample" ：把球的票数当作分布，重新采样 K 组新组合
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np

RED_N = 33
BLUE_N = 16


@dataclass
class AggregatedItem:
    red_balls: list[int]
    blue_ball: int
    score: float
    # consensus 方法下：score = Σ red_votes[r] + 6 × blue_votes[blue]
    # resample 方法下：与上面同公式，让两种方法的分数可比较


@dataclass
class AggregationResult:
    method: str
    source_predictions: int   # 参与聚合的预测条数（Prediction 数）
    source_items: int         # 总组合数
    red_votes: dict[int, int]
    blue_votes: dict[int, int]
    selected: list[AggregatedItem]


def _count_votes(items: list[tuple[list[int], int]]) -> tuple[Counter, Counter]:
    red = Counter()
    blue = Counter()
    for reds, b in items:
        for r in reds:
            red[r] += 1
        blue[b] += 1
    return red, blue


def _score(reds: list[int], blue: int, red_votes: Counter, blue_votes: Counter) -> int:
    """单组得分 = 红球被投票数之和 + 6 × 蓝球被投票数（让蓝球量级与单红球可比）。"""
    return sum(red_votes.get(r, 0) for r in reds) + 6 * blue_votes.get(blue, 0)


def aggregate(
    items: list[tuple[list[int], int]],
    top_k: int = 10,
    method: str = "consensus",
    seed: int | None = None,
    source_predictions: int = 0,
) -> AggregationResult:
    if not items:
        return AggregationResult(method, source_predictions, 0, {}, {}, [])

    red_votes, blue_votes = _count_votes(items)

    if method == "consensus":
        scored = []
        for reds, blue in items:
            scored.append((_score(reds, blue, red_votes, blue_votes), reds, blue))
        scored.sort(key=lambda x: -x[0])

        seen: set[tuple[tuple[int, ...], int]] = set()
        selected: list[AggregatedItem] = []
        for score, reds, blue in scored:
            key = (tuple(reds), blue)
            if key in seen:
                continue
            seen.add(key)
            selected.append(AggregatedItem(red_balls=list(reds), blue_ball=blue, score=float(score)))
            if len(selected) >= top_k:
                break

    elif method == "resample":
        rng = np.random.default_rng(seed)
        red_arr = np.array([red_votes.get(i, 0) + 1 for i in range(1, RED_N + 1)], dtype=float)
        blue_arr = np.array([blue_votes.get(i, 0) + 1 for i in range(1, BLUE_N + 1)], dtype=float)
        red_p = red_arr / red_arr.sum()
        blue_p = blue_arr / blue_arr.sum()

        seen = set()
        selected = []
        attempts = 0
        while len(selected) < top_k and attempts < top_k * 200:
            attempts += 1
            reds_idx = rng.choice(RED_N, size=6, replace=False, p=red_p)
            blue_idx = rng.choice(BLUE_N, p=blue_p)
            reds = sorted(int(x) + 1 for x in reds_idx)
            blue = int(blue_idx) + 1
            key = (tuple(reds), blue)
            if key in seen:
                continue
            seen.add(key)
            selected.append(AggregatedItem(
                red_balls=reds,
                blue_ball=blue,
                score=float(_score(reds, blue, red_votes, blue_votes)),
            ))
    else:
        raise ValueError(f"未知聚合方法: {method}")

    return AggregationResult(
        method=method,
        source_predictions=source_predictions,
        source_items=len(items),
        red_votes=dict(red_votes),
        blue_votes=dict(blue_votes),
        selected=selected,
    )

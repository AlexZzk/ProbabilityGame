"""预测算法集合。"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

import numpy as np

from .schemas import BLUE_MAX, BLUE_MIN, RED_COUNT, RED_MAX, RED_MIN


def _count(values: Iterable[int], lo: int, hi: int) -> Counter:
    c = Counter({n: 0 for n in range(lo, hi + 1)})
    for v in values:
        c[v] += 1
    return c


def compute_frequencies(draws: list[tuple[list[int], int]]) -> tuple[Counter, Counter]:
    """统计红/蓝球历史出现次数。draws: [(reds, blue), ...]"""
    reds = [r for reds, _ in draws for r in reds]
    blues = [b for _, b in draws]
    return _count(reds, RED_MIN, RED_MAX), _count(blues, BLUE_MIN, BLUE_MAX)


def _weighted_sample_reds(weights: np.ndarray, rng: np.random.Generator) -> list[int]:
    """从 1..33 中按权重不放回抽 6 个。"""
    p = weights / weights.sum()
    chosen = rng.choice(np.arange(RED_MIN, RED_MAX + 1), size=RED_COUNT, replace=False, p=p)
    return sorted(int(x) for x in chosen)


def _weighted_pick_blue(weights: np.ndarray, rng: np.random.Generator) -> int:
    p = weights / weights.sum()
    return int(rng.choice(np.arange(BLUE_MIN, BLUE_MAX + 1), p=p))


def _smooth(counter: Counter, lo: int, hi: int, alpha: float = 1.0) -> np.ndarray:
    """Laplace 平滑，避免 0 概率。"""
    return np.array([counter.get(n, 0) + alpha for n in range(lo, hi + 1)], dtype=float)


def predict(
    draws: list[tuple[list[int], int]],
    count: int,
    strategy: str = "frequency_weighted",
    seed: int | None = None,
) -> list[tuple[list[int], int]]:
    """生成 count 个 (red_balls, blue_ball) 预测组合。

    策略说明：
    - frequency_weighted: 按历史频率（平滑后）作为权重加权随机
    - hot:                选历史出现最多的 6 红 + 最多的 1 蓝（每次小幅扰动避免重复）
    - cold:               反之，选最冷的
    - balanced:           红球 = 3 热 + 3 冷，蓝球随机一个中等频次
    - scarcity:           偏好「历史从未一起出现过」的稀缺组合（频率倒数加权）
    - random:             完全均匀随机
    """
    rng = np.random.default_rng(seed)
    red_cnt, blue_cnt = compute_frequencies(draws) if draws else (Counter(), Counter())

    red_freq = _smooth(red_cnt, RED_MIN, RED_MAX, alpha=1.0)
    blue_freq = _smooth(blue_cnt, BLUE_MIN, BLUE_MAX, alpha=1.0)

    results: list[tuple[list[int], int]] = []
    seen: set[tuple[tuple[int, ...], int]] = set()

    # 历史出现过的二元组（用于 scarcity 评估）
    pair_seen: Counter = Counter()
    for reds, _ in draws:
        rs = sorted(reds)
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                pair_seen[(rs[i], rs[j])] += 1

    def pair_score(reds: list[int]) -> float:
        """组合稀缺度：内部二元组的历史出现总和越小越稀缺。"""
        s = 0
        rs = sorted(reds)
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                s += pair_seen.get((rs[i], rs[j]), 0)
        return s

    attempts = 0
    while len(results) < count and attempts < count * 200:
        attempts += 1

        if strategy == "frequency_weighted":
            reds = _weighted_sample_reds(red_freq, rng)
            blue = _weighted_pick_blue(blue_freq, rng)

        elif strategy == "hot":
            order = np.argsort(-red_freq + rng.normal(0, 0.1, size=red_freq.size))
            reds = sorted(int(RED_MIN + i) for i in order[:RED_COUNT])
            blue = int(BLUE_MIN + int(np.argmax(blue_freq + rng.normal(0, 0.1, size=blue_freq.size))))

        elif strategy == "cold":
            order = np.argsort(red_freq + rng.normal(0, 0.1, size=red_freq.size))
            reds = sorted(int(RED_MIN + i) for i in order[:RED_COUNT])
            blue = int(BLUE_MIN + int(np.argmin(blue_freq + rng.normal(0, 0.1, size=blue_freq.size))))

        elif strategy == "balanced":
            hot_order = np.argsort(-red_freq + rng.normal(0, 0.1, size=red_freq.size))
            cold_order = np.argsort(red_freq + rng.normal(0, 0.1, size=red_freq.size))
            hot_pick = [int(RED_MIN + i) for i in hot_order[:3]]
            cold_pick = [int(RED_MIN + i) for i in cold_order if int(RED_MIN + i) not in hot_pick][:3]
            reds = sorted(hot_pick + cold_pick)
            blue = _weighted_pick_blue(np.ones_like(blue_freq), rng)

        elif strategy == "scarcity":
            # 采样若干候选，挑稀缺度最低的
            candidates = []
            for _ in range(20):
                rs = _weighted_sample_reds(1.0 / red_freq, rng)
                candidates.append((pair_score(rs), rs))
            candidates.sort(key=lambda x: x[0])
            reds = candidates[0][1]
            blue = _weighted_pick_blue(1.0 / blue_freq, rng)

        elif strategy == "random":
            reds = sorted(int(x) for x in rng.choice(
                np.arange(RED_MIN, RED_MAX + 1), size=RED_COUNT, replace=False
            ))
            blue = int(rng.integers(BLUE_MIN, BLUE_MAX + 1))

        else:
            raise ValueError(f"未知策略: {strategy}")

        key = (tuple(reds), blue)
        if key in seen:
            continue
        seen.add(key)
        results.append((reds, blue))

    return results

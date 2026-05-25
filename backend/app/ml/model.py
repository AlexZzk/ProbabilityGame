"""自适应 Dirichlet-Multinomial 预测模型。

设计目标：用最小可解释的代价，演示一套完整的 ML 训练范式
（参数 → 前向 → 损失 → 梯度/计数更新 → 校准 → 自调整）。

数学模型
========

把每期的 7 个号码当作两个独立的多项分布观测：
- 红球：从 33 类里不放回抽 6 次，每类边缘出现概率 p_red[i]
- 蓝球：从 16 类里抽 1 次，每类概率 p_blue[j]

我们对每个类的概率引入 Dirichlet 共轭先验，
后验等价于一组「伪计数」α[i]，满足
    p[i] = α[i] / Σα

为了控制「模型对训练数据相信多少」，我们再加一个温度 T：
    p_T[i] = α[i]^(1/T) / Σ α[k]^(1/T)

- T → ∞ 时分布趋向均匀（完全不相信历史，回退到「公平」假设）
- T → 0 时分布趋向 one-hot（极端相信历史）
- T = 1 时即标准后验

训练（在线学习）
================
每来一期真实开奖 D_t = (reds_t, blue_t)：
  1. 计算训练前的 NLL 损失（用于评估当前模型质量）
       L = -Σ log p_red[r] - log p_blue[b]
  2. 衰减老计数（可选，模拟近期数据权重更大）
       α ← α * decay
  3. 把观测加入计数
       α_red[r] += η,  α_blue[b] += η

自校准
======
每隔若干步，用最近 W 期开奖作为「经验分布」 q，与模型分布 p 比较：
  KL_model    = KL(q ‖ p)        模型距离真实有多远
  KL_uniform  = KL(q ‖ 1/N)      均匀分布距离真实有多远

若 KL_model > KL_uniform + ε：模型过拟合了过去的噪声，升温
若 KL_model < KL_uniform - ε：模型确实抓到了真实偏差，降温
否则保持不变。

这就是一个最小但完整的「自适应预测器」：
拿到反馈 → 量化偏差 → 修正自身。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

RED_N = 33
BLUE_N = 16

EPS = 1e-9


@dataclass
class ModelParams:
    """模型可学习状态。所有更新都体现在这里。"""

    red_alpha: np.ndarray   # shape (33,)
    blue_alpha: np.ndarray  # shape (16,)
    temperature: float = 1.0
    learning_rate: float = 1.0       # 每次观测对计数的贡献
    decay: float = 1.0               # 旧计数衰减系数，1.0 = 不衰减
    version: int = 0                 # 累计训练步数

    @classmethod
    def fresh(cls, prior_strength: float = 1.0) -> "ModelParams":
        return cls(
            red_alpha=np.full(RED_N, prior_strength, dtype=float),
            blue_alpha=np.full(BLUE_N, prior_strength, dtype=float),
        )

    # --- 前向：把参数转成概率分布 -----------------------------

    def red_probs(self) -> np.ndarray:
        return _tempered(self.red_alpha, self.temperature)

    def blue_probs(self) -> np.ndarray:
        return _tempered(self.blue_alpha, self.temperature)


def _tempered(alpha: np.ndarray, T: float) -> np.ndarray:
    """带温度的归一化。T 越大越均匀。"""
    # 用 log 域避免 0 或 inf
    log_a = np.log(np.clip(alpha, EPS, None)) / max(T, EPS)
    log_a -= log_a.max()  # 数值稳定
    p = np.exp(log_a)
    return p / p.sum()


# ---------------- 训练：单步 ------------------------------------

@dataclass
class TrainStepResult:
    nll: float
    nll_red: float
    nll_blue: float
    temperature_before: float
    temperature_after: float
    version_before: int
    version_after: int


def train_step(
    params: ModelParams,
    reds: list[int],
    blue: int,
) -> TrainStepResult:
    """处理一条新观测，原地更新 params。

    步骤严格对应文档：先算损失（评估当前模型）→ 衰减 → 增加计数。
    """
    p_red = params.red_probs()
    p_blue = params.blue_probs()

    # NLL on this observation (在更新前评估，等价于 hold-out 的瞬时损失)
    red_idx = np.array([r - 1 for r in reds], dtype=int)
    nll_red = float(-np.log(p_red[red_idx] + EPS).sum())
    nll_blue = float(-np.log(p_blue[blue - 1] + EPS))
    nll = nll_red + nll_blue

    t_before = params.temperature
    v_before = params.version

    # 衰减老计数（如果 decay<1，等价于指数移动平均）
    if params.decay < 1.0:
        params.red_alpha *= params.decay
        params.blue_alpha *= params.decay

    # 累积新观测
    for r in reds:
        params.red_alpha[r - 1] += params.learning_rate
    params.blue_alpha[blue - 1] += params.learning_rate

    params.version += 1

    return TrainStepResult(
        nll=nll,
        nll_red=nll_red,
        nll_blue=nll_blue,
        temperature_before=t_before,
        temperature_after=params.temperature,
        version_before=v_before,
        version_after=params.version,
    )


# ---------------- 自校准 ----------------------------------------

@dataclass
class CalibrationResult:
    kl_red_vs_model: float
    kl_red_vs_uniform: float
    kl_blue_vs_model: float
    kl_blue_vs_uniform: float
    temperature_before: float
    temperature_after: float
    decision: str


def _kl(p: np.ndarray, q: np.ndarray) -> float:
    p = p + EPS
    q = q + EPS
    return float(np.sum(p * np.log(p / q)))


def calibrate(
    params: ModelParams,
    recent_draws: list[tuple[list[int], int]],
    min_samples: int = 10,
    margin: float = 0.01,
    temp_up: float = 1.10,
    temp_down: float = 0.95,
    temp_min: float = 0.5,
    temp_max: float = 10.0,
) -> CalibrationResult | None:
    """用最近 W 期的经验分布反过来评估并调整模型温度。"""
    if len(recent_draws) < min_samples:
        return None

    red_emp = np.zeros(RED_N)
    blue_emp = np.zeros(BLUE_N)
    for reds, b in recent_draws:
        for r in reds:
            red_emp[r - 1] += 1
        blue_emp[b - 1] += 1
    red_emp = red_emp / red_emp.sum()
    blue_emp = blue_emp / blue_emp.sum()

    p_red = params.red_probs()
    p_blue = params.blue_probs()
    uni_red = np.full(RED_N, 1.0 / RED_N)
    uni_blue = np.full(BLUE_N, 1.0 / BLUE_N)

    kl_red_model = _kl(red_emp, p_red)
    kl_red_unif = _kl(red_emp, uni_red)
    kl_blue_model = _kl(blue_emp, p_blue)
    kl_blue_unif = _kl(blue_emp, uni_blue)

    # 综合红/蓝的总 KL 差距来决策
    diff = (kl_red_model + kl_blue_model) - (kl_red_unif + kl_blue_unif)

    t_before = params.temperature
    if diff > margin:
        params.temperature = min(params.temperature * temp_up, temp_max)
        decision = "raise"  # 模型比均匀差，回退
    elif diff < -margin:
        params.temperature = max(params.temperature * temp_down, temp_min)
        decision = "lower"  # 模型比均匀好，敢更尖
    else:
        decision = "keep"

    return CalibrationResult(
        kl_red_vs_model=kl_red_model,
        kl_red_vs_uniform=kl_red_unif,
        kl_blue_vs_model=kl_blue_model,
        kl_blue_vs_uniform=kl_blue_unif,
        temperature_before=t_before,
        temperature_after=params.temperature,
        decision=decision,
    )


# ---------------- 采样：根据当前分布生成预测 ---------------------

def sample_predictions(
    params: ModelParams,
    count: int,
    seed: int | None = None,
) -> list[tuple[list[int], int]]:
    rng = np.random.default_rng(seed)
    p_red = params.red_probs()
    p_blue = params.blue_probs()

    results: list[tuple[list[int], int]] = []
    seen: set[tuple[tuple[int, ...], int]] = set()
    attempts = 0
    while len(results) < count and attempts < count * 200:
        attempts += 1
        reds_idx = rng.choice(RED_N, size=6, replace=False, p=p_red)
        blue_idx = rng.choice(BLUE_N, p=p_blue)
        reds = sorted(int(x) + 1 for x in reds_idx)
        blue = int(blue_idx) + 1
        key = (tuple(reds), blue)
        if key in seen:
            continue
        seen.add(key)
        results.append((reds, blue))
    return results

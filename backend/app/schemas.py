from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RED_MIN, RED_MAX, RED_COUNT = 1, 33, 6
BLUE_MIN, BLUE_MAX = 1, 16


def _validate_reds(v: list[int]) -> list[int]:
    if len(v) != RED_COUNT:
        raise ValueError(f"红球必须是 {RED_COUNT} 个")
    if len(set(v)) != RED_COUNT:
        raise ValueError("红球不能重复")
    for n in v:
        if not RED_MIN <= n <= RED_MAX:
            raise ValueError(f"红球必须在 {RED_MIN}-{RED_MAX} 之间")
    return sorted(v)


def _validate_blue(v: int) -> int:
    if not BLUE_MIN <= v <= BLUE_MAX:
        raise ValueError(f"蓝球必须在 {BLUE_MIN}-{BLUE_MAX} 之间")
    return v


class DrawIn(BaseModel):
    period: str
    red_balls: list[int]
    blue_ball: int
    draw_date: datetime | None = None

    @field_validator("red_balls")
    @classmethod
    def _v_red(cls, v): return _validate_reds(v)

    @field_validator("blue_ball")
    @classmethod
    def _v_blue(cls, v): return _validate_blue(v)


class DrawOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period: str
    red_balls: list[int]
    blue_ball: int
    draw_date: datetime | None
    created_at: datetime


class BulkDrawIn(BaseModel):
    draws: list[DrawIn]


Strategy = Literal["frequency_weighted", "hot", "cold", "balanced", "scarcity", "random", "adaptive"]


class PredictRequest(BaseModel):
    count: int = Field(ge=1, le=100, default=5)
    strategy: Strategy = "frequency_weighted"
    target_period: str | None = None
    notes: str | None = None
    # 频率统计窗口（仅取最近 N 期），None 表示全部
    window: int | None = Field(default=None, ge=10)


class BacktestRequest(BaseModel):
    """对已有的某一期做回测：只用该期之前的数据训练并预测，然后立即评估。"""

    target_period: str
    count: int = Field(ge=1, le=100, default=5)
    strategy: Strategy = "adaptive"
    notes: str | None = None


class PredictionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    red_balls: list[int]
    blue_ball: int
    red_hits: int | None
    blue_hit: bool | None
    prize_level: int | None


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy: str
    count: int
    target_period: str | None
    notes: str | None
    created_at: datetime
    items: list[PredictionItemOut]


AggregateMethod = Literal["consensus", "resample"]


class AggregateRequest(BaseModel):
    """把若干预测聚合成 top_k 注最终组合。

    至少提供 prediction_ids 或 target_period 之一；同时给出时取交集。
    """

    prediction_ids: list[int] | None = None
    target_period: str | None = None
    strategy: str | None = None  # 可选过滤
    top_k: int = Field(ge=1, le=100, default=10)
    method: AggregateMethod = "consensus"
    seed: int | None = None


class AggregatedItemOut(BaseModel):
    red_balls: list[int]
    blue_ball: int
    score: float


class AggregateResponse(BaseModel):
    method: str
    source_predictions: int
    source_items: int
    red_votes: dict[int, int]
    blue_votes: dict[int, int]
    selected: list[AggregatedItemOut]


class HistoryGroup(BaseModel):
    """以期号为单位聚合的预测历史。"""

    target_period: str | None  # None 表示「未指定期号」分组
    draw: DrawOut | None
    predictions: list[PredictionOut]
    # 汇总
    prediction_count: int
    item_count: int
    evaluated_count: int
    hit_count: int  # 中奖（prize_level > 0）数


class FrequencyStats(BaseModel):
    red: dict[int, int]
    blue: dict[int, int]
    total_draws: int


class ModelStateOut(BaseModel):
    name: str
    version: int
    temperature: float
    learning_rate: float
    decay: float
    prior_strength: float
    last_trained_draw_id: int | None
    red_alpha: list[float]
    blue_alpha: list[float]
    red_probs: list[float]
    blue_probs: list[float]
    updated_at: str | None


class ModelTrainResponse(BaseModel):
    trained: int
    calibrated: int
    version: int


class ModelEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    version: int
    draw_id: int | None
    nll: float | None
    nll_red: float | None
    nll_blue: float | None
    temperature_before: float | None
    temperature_after: float | None
    kl_red_vs_model: float | None
    kl_red_vs_uniform: float | None
    kl_blue_vs_model: float | None
    kl_blue_vs_uniform: float | None
    decision: str | None
    created_at: datetime

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


Strategy = Literal["frequency_weighted", "hot", "cold", "balanced", "scarcity", "random"]


class PredictRequest(BaseModel):
    count: int = Field(ge=1, le=100, default=5)
    strategy: Strategy = "frequency_weighted"
    target_period: str | None = None
    notes: str | None = None
    # 频率统计窗口（仅取最近 N 期），None 表示全部
    window: int | None = Field(default=None, ge=10)


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


class FrequencyStats(BaseModel):
    red: dict[int, int]
    blue: dict[int, int]
    total_draws: int

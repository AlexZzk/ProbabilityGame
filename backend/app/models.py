from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Draw(Base):
    """一期真实开奖记录，也是预测的训练集。"""

    __tablename__ = "draws"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    red_balls: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    blue_ball: Mapped[int] = mapped_column(Integer, nullable=False)
    draw_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Prediction(Base):
    """一次预测调用产生的批次。"""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    target_period: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    items: Mapped[list["PredictionItem"]] = relationship(
        back_populates="prediction", cascade="all, delete-orphan"
    )


class PredictionItem(Base):
    """单条预测组合。"""

    __tablename__ = "prediction_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("predictions.id", ondelete="CASCADE"), index=True
    )
    red_balls: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    blue_ball: Mapped[int] = mapped_column(Integer, nullable=False)

    # 评估结果（在真实开奖录入后回填）
    matched_draw_id: Mapped[int | None] = mapped_column(
        ForeignKey("draws.id", ondelete="SET NULL"), nullable=True
    )
    red_hits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blue_hit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    prize_level: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0=未中奖

    prediction: Mapped[Prediction] = relationship(back_populates="items")

    __table_args__ = (
        UniqueConstraint("prediction_id", "id", name="uq_prediction_item"),
    )


class ModelState(Base):
    """自适应预测模型的可学习参数快照（同一 name 同步原地更新）。"""

    __tablename__ = "model_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    red_alpha: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    blue_alpha: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    learning_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    decay: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    prior_strength: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 已经训练过的最大 draw_id，避免重复训练
    last_trained_draw_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ModelTrainingEvent(Base):
    """每次训练步 / 校准事件的日志，用于画训练曲线。"""

    __tablename__ = "model_training_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_state_id: Mapped[int] = mapped_column(
        ForeignKey("model_states.id", ondelete="CASCADE"), index=True
    )
    draw_id: Mapped[int | None] = mapped_column(
        ForeignKey("draws.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # train | calibrate | reset

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    nll: Mapped[float | None] = mapped_column(Float, nullable=True)
    nll_red: Mapped[float | None] = mapped_column(Float, nullable=True)
    nll_blue: Mapped[float | None] = mapped_column(Float, nullable=True)

    temperature_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_after: Mapped[float | None] = mapped_column(Float, nullable=True)

    kl_red_vs_model: Mapped[float | None] = mapped_column(Float, nullable=True)
    kl_red_vs_uniform: Mapped[float | None] = mapped_column(Float, nullable=True)
    kl_blue_vs_model: Mapped[float | None] = mapped_column(Float, nullable=True)
    kl_blue_vs_uniform: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(16), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

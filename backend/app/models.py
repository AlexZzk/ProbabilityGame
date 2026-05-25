from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
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

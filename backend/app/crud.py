from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from . import models, schemas
from .evaluator import evaluate


# ---------- Draws ----------

def upsert_draw(db: Session, payload: schemas.DrawIn) -> models.Draw:
    existing = db.scalar(select(models.Draw).where(models.Draw.period == payload.period))
    if existing:
        existing.red_balls = payload.red_balls
        existing.blue_ball = payload.blue_ball
        existing.draw_date = payload.draw_date
        db.flush()
        return existing
    draw = models.Draw(
        period=payload.period,
        red_balls=payload.red_balls,
        blue_ball=payload.blue_ball,
        draw_date=payload.draw_date,
    )
    db.add(draw)
    db.flush()
    return draw


def list_draws(db: Session, limit: int = 200, offset: int = 0) -> list[models.Draw]:
    return list(db.scalars(
        select(models.Draw).order_by(desc(models.Draw.period)).limit(limit).offset(offset)
    ))


def count_draws(db: Session) -> int:
    return db.scalar(select(func.count(models.Draw.id))) or 0


def all_draws_for_training(db: Session, window: int | None = None) -> list[models.Draw]:
    q = select(models.Draw).order_by(desc(models.Draw.period))
    if window:
        q = q.limit(window)
    return list(db.scalars(q))


def get_draw_by_period(db: Session, period: str) -> models.Draw | None:
    return db.scalar(select(models.Draw).where(models.Draw.period == period))


# ---------- Predictions ----------

def create_prediction(
    db: Session,
    strategy: str,
    count: int,
    items: list[tuple[list[int], int]],
    target_period: str | None = None,
    notes: str | None = None,
) -> models.Prediction:
    pred = models.Prediction(
        strategy=strategy, count=count, target_period=target_period, notes=notes
    )
    db.add(pred)
    db.flush()
    for reds, blue in items:
        db.add(models.PredictionItem(
            prediction_id=pred.id, red_balls=reds, blue_ball=blue,
        ))
    db.flush()
    return get_prediction(db, pred.id)  # type: ignore[return-value]


def get_prediction(db: Session, prediction_id: int) -> models.Prediction | None:
    return db.scalar(
        select(models.Prediction)
        .options(selectinload(models.Prediction.items))
        .where(models.Prediction.id == prediction_id)
    )


def list_predictions(db: Session, limit: int = 50) -> list[models.Prediction]:
    return list(db.scalars(
        select(models.Prediction)
        .options(selectinload(models.Prediction.items))
        .order_by(desc(models.Prediction.created_at))
        .limit(limit)
    ))


def evaluate_predictions_against(db: Session, draw: models.Draw) -> int:
    """对所有 target_period == draw.period 的预测条目回填评估，返回更新条数。"""
    preds = list(db.scalars(
        select(models.Prediction)
        .options(selectinload(models.Prediction.items))
        .where(models.Prediction.target_period == draw.period)
    ))
    updated = 0
    for p in preds:
        for item in p.items:
            red_hits, blue_hit, level = evaluate(
                item.red_balls, item.blue_ball, draw.red_balls, draw.blue_ball
            )
            item.matched_draw_id = draw.id
            item.red_hits = red_hits
            item.blue_hit = blue_hit
            item.prize_level = level
            updated += 1
    db.flush()
    return updated

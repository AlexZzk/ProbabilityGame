from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=list[schemas.HistoryGroup])
def grouped_history(limit_periods: int = 100, db: Session = Depends(get_db)):
    """按目标期号聚合的历史。每组包含该期真实开奖（若已录入）和所有相关预测。

    返回按期号倒序；`target_period` 为 None 的组放最末，归为「未指定期号」。
    """
    # 拉所有 predictions（含 items）
    preds = list(db.scalars(
        select(models.Prediction)
        .options(selectinload(models.Prediction.items))
        .order_by(desc(models.Prediction.created_at))
    ))

    grouped: dict[str | None, list[models.Prediction]] = {}
    for p in preds:
        grouped.setdefault(p.target_period, []).append(p)

    # 排序：有期号的按期号倒序，None 放最后
    keys = sorted([k for k in grouped if k is not None], reverse=True)[:limit_periods]
    has_none = None in grouped

    result: list[schemas.HistoryGroup] = []
    for period in keys:
        draw = crud.get_draw_by_period(db, period)
        plist = grouped[period]
        result.append(_make_group(period, draw, plist))

    if has_none:
        result.append(_make_group(None, None, grouped[None]))

    return result


def _make_group(
    period: str | None,
    draw: models.Draw | None,
    preds: list[models.Prediction],
) -> schemas.HistoryGroup:
    items = [it for p in preds for it in p.items]
    evaluated = [it for it in items if it.prize_level is not None]
    hits = [it for it in evaluated if (it.prize_level or 0) > 0]
    return schemas.HistoryGroup(
        target_period=period,
        draw=schemas.DrawOut.model_validate(draw) if draw else None,
        predictions=[schemas.PredictionOut.model_validate(p) for p in preds],
        prediction_count=len(preds),
        item_count=len(items),
        evaluated_count=len(evaluated),
        hit_count=len(hits),
    )

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .. import aggregator, crud, models, schemas
from ..database import get_db
from ..ml import service as ml_service
from ..predictor import predict

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.post("", response_model=schemas.PredictionOut, status_code=status.HTTP_201_CREATED)
def create_prediction(req: schemas.PredictRequest, db: Session = Depends(get_db)):
    if req.strategy == "adaptive":
        # 自适应模型：用持久化的 ModelParams 采样，先确保最新数据已训练
        ml_service.train_on_new_draws(db)
        items = ml_service.predict_with_model(db, count=req.count)
    else:
        draws = crud.all_draws_for_training(db, window=req.window)
        if not draws and req.strategy != "random":
            raise HTTPException(400, "训练集为空，无法基于历史预测；请先上传开奖数据，或使用 random 策略")
        items = predict(
            [(d.red_balls, d.blue_ball) for d in draws],
            count=req.count,
            strategy=req.strategy,
        )
    pred = crud.create_prediction(
        db,
        strategy=req.strategy,
        count=req.count,
        items=items,
        target_period=req.target_period,
        notes=req.notes,
    )
    db.commit()
    return pred


@router.post("/backtest", response_model=schemas.PredictionOut, status_code=status.HTTP_201_CREATED)
def backtest(req: schemas.BacktestRequest, db: Session = Depends(get_db)):
    """用「目标期之前的数据」从零训练并预测目标期，然后立即评估。

    注意：这条预测会被保存为一条带 [backtest] 备注的 Prediction 记录，
    可在「历史与评估」页面查看。临时模型不会污染主模型状态。
    """
    target_draw = crud.get_draw_by_period(db, req.target_period)
    if not target_draw:
        raise HTTPException(400, f"期号 {req.target_period} 尚未录入真实开奖，无法回测")

    prior_draws = crud.draws_before_period(db, req.target_period)
    if not prior_draws and req.strategy != "random":
        raise HTTPException(400, f"{req.target_period} 之前没有任何开奖数据，无法回测（除非用 random 策略）")

    if req.strategy == "adaptive":
        params = ml_service.train_temp_model_on(
            [(d.red_balls, d.blue_ball) for d in prior_draws]
        )
        items = ml_service.sample_from_params(params, count=req.count)
    else:
        items = predict(
            [(d.red_balls, d.blue_ball) for d in prior_draws],
            count=req.count,
            strategy=req.strategy,
        )

    notes = f"[backtest] {req.notes}" if req.notes else "[backtest]"
    pred = crud.create_prediction(
        db,
        strategy=req.strategy,
        count=req.count,
        items=items,
        target_period=req.target_period,
        notes=notes,
    )
    # 立即用真实开奖评估
    crud.evaluate_predictions_against(db, target_draw)
    db.commit()
    return crud.get_prediction(db, pred.id)


@router.post("/aggregate", response_model=schemas.AggregateResponse)
def aggregate_predictions(req: schemas.AggregateRequest, db: Session = Depends(get_db)):
    """对一批预测做投票聚合，给出 top_k 注最终组合。

    - 至少需要 prediction_ids 或 target_period 之一
    - 默认 method=consensus（从候选里挑共识最高的 K 注，不生成新组合）
    - method=resample 时按投票频率重新采样 K 注新组合
    """
    if not req.prediction_ids and not req.target_period:
        raise HTTPException(400, "请提供 prediction_ids 或 target_period 之一")

    q = (
        select(models.Prediction)
        .options(selectinload(models.Prediction.items))
    )
    if req.prediction_ids:
        q = q.where(models.Prediction.id.in_(req.prediction_ids))
    if req.target_period:
        q = q.where(models.Prediction.target_period == req.target_period)
    if req.strategy:
        q = q.where(models.Prediction.strategy == req.strategy)

    preds = list(db.scalars(q))
    if not preds:
        raise HTTPException(404, "没有匹配的预测记录")

    items = [(it.red_balls, it.blue_ball) for p in preds for it in p.items]
    result = aggregator.aggregate(
        items,
        top_k=req.top_k,
        method=req.method,
        seed=req.seed,
        source_predictions=len(preds),
    )
    return schemas.AggregateResponse(
        method=result.method,
        source_predictions=result.source_predictions,
        source_items=result.source_items,
        red_votes=result.red_votes,
        blue_votes=result.blue_votes,
        selected=[
            schemas.AggregatedItemOut(
                red_balls=it.red_balls, blue_ball=it.blue_ball, score=it.score
            )
            for it in result.selected
        ],
    )


@router.get("", response_model=list[schemas.PredictionOut])
def list_predictions(limit: int = 50, db: Session = Depends(get_db)):
    return crud.list_predictions(db, limit=limit)


@router.get("/{prediction_id}", response_model=schemas.PredictionOut)
def get_prediction(prediction_id: int, db: Session = Depends(get_db)):
    pred = crud.get_prediction(db, prediction_id)
    if not pred:
        raise HTTPException(404, "预测不存在")
    return pred

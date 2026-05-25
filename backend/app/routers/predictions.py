from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..predictor import predict

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.post("", response_model=schemas.PredictionOut, status_code=status.HTTP_201_CREATED)
def create_prediction(req: schemas.PredictRequest, db: Session = Depends(get_db)):
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


@router.get("", response_model=list[schemas.PredictionOut])
def list_predictions(limit: int = 50, db: Session = Depends(get_db)):
    return crud.list_predictions(db, limit=limit)


@router.get("/{prediction_id}", response_model=schemas.PredictionOut)
def get_prediction(prediction_id: int, db: Session = Depends(get_db)):
    pred = crud.get_prediction(db, prediction_id)
    if not pred:
        raise HTTPException(404, "预测不存在")
    return pred

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..ml import service

router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("", response_model=schemas.ModelStateOut)
def get_state(db: Session = Depends(get_db)):
    snap = service.get_state_snapshot(db)
    db.commit()  # 可能首次访问会创建 state 行
    return snap


@router.post("/train", response_model=schemas.ModelTrainResponse)
def train(
    full_retrain: bool = False,
    calibrate_every: int = 5,
    db: Session = Depends(get_db),
):
    """对所有未训练过的开奖进行在线训练；可选 full_retrain=True 从零开始。"""
    result = service.train_on_new_draws(
        db, full_retrain=full_retrain, calibrate_every=calibrate_every
    )
    db.commit()
    return result


@router.post("/reset", response_model=schemas.ModelStateOut)
def reset(prior_strength: float | None = None, db: Session = Depends(get_db)):
    service.reset_model(db, prior_strength=prior_strength)
    snap = service.get_state_snapshot(db)
    db.commit()
    return snap


@router.get("/events", response_model=list[schemas.ModelEventOut])
def list_events(limit: int = 500, db: Session = Depends(get_db)):
    rows = service.list_events(db, limit=limit)
    db.commit()
    return rows

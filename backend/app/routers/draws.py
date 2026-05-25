from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..ml import service as ml_service
from ..predictor import compute_frequencies

router = APIRouter(prefix="/api/draws", tags=["draws"])


@router.get("", response_model=list[schemas.DrawOut])
def list_draws(limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    return crud.list_draws(db, limit=limit, offset=offset)


@router.get("/count")
def count_draws(db: Session = Depends(get_db)):
    return {"total": crud.count_draws(db)}


@router.post("", response_model=schemas.DrawOut, status_code=status.HTTP_201_CREATED)
def create_draw(payload: schemas.DrawIn, db: Session = Depends(get_db)):
    draw = crud.upsert_draw(db, payload)
    crud.evaluate_predictions_against(db, draw)
    # 在线训练：把新一期喂给自适应模型
    ml_service.train_on_new_draws(db)
    db.commit()
    db.refresh(draw)
    return draw


@router.post("/bulk", response_model=dict)
def bulk_create(payload: schemas.BulkDrawIn, db: Session = Depends(get_db)):
    inserted = 0
    for d in payload.draws:
        crud.upsert_draw(db, d)
        inserted += 1
    ml_service.train_on_new_draws(db)
    db.commit()
    return {"inserted_or_updated": inserted}


def _parse_csv(text: str) -> list[schemas.DrawIn]:
    """CSV 列: period,red1,red2,red3,red4,red5,red6,blue[,draw_date]"""
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    header = [c.strip().lower() for c in rows[0]]
    if "period" in header:
        rows = rows[1:]

    out: list[schemas.DrawIn] = []
    for i, row in enumerate(rows, start=2):
        if not row or all(not c.strip() for c in row):
            continue
        if len(row) < 8:
            raise HTTPException(400, f"第 {i} 行列数不足 8（period + 6红 + 1蓝）")
        try:
            period = row[0].strip()
            reds = [int(row[j]) for j in range(1, 7)]
            blue = int(row[7])
            draw_date = None
            if len(row) >= 9 and row[8].strip():
                try:
                    draw_date = datetime.fromisoformat(row[8].strip())
                except ValueError:
                    draw_date = None
            out.append(schemas.DrawIn(
                period=period, red_balls=reds, blue_ball=blue, draw_date=draw_date
            ))
        except ValueError as e:
            raise HTTPException(400, f"第 {i} 行解析失败: {e}") from e
    return out


@router.post("/upload", response_model=dict)
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = (await file.read()).decode("utf-8-sig")
    draws = _parse_csv(content)
    for d in draws:
        crud.upsert_draw(db, d)
    ml_service.train_on_new_draws(db)
    db.commit()
    return {"inserted_or_updated": len(draws)}


@router.put("/{draw_id}", response_model=schemas.DrawOut)
def update_draw(draw_id: int, payload: schemas.DrawIn, db: Session = Depends(get_db)):
    draw = crud.get_draw(db, draw_id)
    if not draw:
        raise HTTPException(404, "开奖记录不存在")
    old_period = draw.period
    try:
        crud.update_draw(db, draw, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    # 老期号关联的预测可能需要清除评估（不再匹配）
    if old_period != draw.period:
        crud.clear_evaluations_for_period(db, old_period)
    # 新期号匹配的预测重新评估
    crud.evaluate_predictions_against(db, draw)
    # 历史数据被改了，主模型必须全量重训
    ml_service.mark_stale_and_retrain(db)
    db.commit()
    db.refresh(draw)
    return draw


@router.delete("/{draw_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draw(draw_id: int, db: Session = Depends(get_db)):
    draw = crud.get_draw(db, draw_id)
    if not draw:
        raise HTTPException(404, "开奖记录不存在")
    period = draw.period
    crud.delete_draw(db, draw)
    crud.clear_evaluations_for_period(db, period)
    ml_service.mark_stale_and_retrain(db)
    db.commit()
    return None


@router.get("/stats/frequency", response_model=schemas.FrequencyStats)
def frequency(window: int | None = None, db: Session = Depends(get_db)):
    draws = crud.all_draws_for_training(db, window=window)
    red, blue = compute_frequencies([(d.red_balls, d.blue_ball) for d in draws])
    return schemas.FrequencyStats(
        red={k: v for k, v in sorted(red.items())},
        blue={k: v for k, v in sorted(blue.items())},
        total_draws=len(draws),
    )

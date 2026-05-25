"""模型的高层接口：训练、校准、预测、写日志。

唯一被 router / 自动训练逻辑调用的入口。
"""
from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .. import models
from . import persistence
from .model import (
    CalibrationResult,
    ModelParams,
    TrainStepResult,
    calibrate,
    sample_predictions,
    train_step,
)


CALIBRATION_WINDOW = 50  # 用最近多少期做经验分布


def _log_train(
    db: Session,
    state_row: models.ModelState,
    draw_id: int | None,
    res: TrainStepResult,
) -> None:
    db.add(models.ModelTrainingEvent(
        model_state_id=state_row.id,
        draw_id=draw_id,
        event_type="train",
        version=res.version_after,
        nll=res.nll,
        nll_red=res.nll_red,
        nll_blue=res.nll_blue,
        temperature_before=res.temperature_before,
        temperature_after=res.temperature_after,
    ))


def _log_calibrate(
    db: Session,
    state_row: models.ModelState,
    params: ModelParams,
    cal: CalibrationResult,
) -> None:
    db.add(models.ModelTrainingEvent(
        model_state_id=state_row.id,
        draw_id=None,
        event_type="calibrate",
        version=params.version,
        temperature_before=cal.temperature_before,
        temperature_after=cal.temperature_after,
        kl_red_vs_model=cal.kl_red_vs_model,
        kl_red_vs_uniform=cal.kl_red_vs_uniform,
        kl_blue_vs_model=cal.kl_blue_vs_model,
        kl_blue_vs_uniform=cal.kl_blue_vs_uniform,
        decision=cal.decision,
    ))


def _log_reset(db: Session, state_row: models.ModelState) -> None:
    db.add(models.ModelTrainingEvent(
        model_state_id=state_row.id,
        event_type="reset",
        version=0,
        temperature_before=None,
        temperature_after=state_row.temperature,
    ))


def train_on_new_draws(
    db: Session,
    *,
    calibrate_every: int = 5,
    full_retrain: bool = False,
) -> dict:
    """处理所有还没被模型见过的 draw（按 id 升序），做在线训练。

    每 `calibrate_every` 步触发一次自校准。返回汇总信息。
    """
    state_row, params = persistence.load_or_init(db)

    if full_retrain:
        params = persistence.reset(state_row)
        _log_reset(db, state_row)

    last_seen = state_row.last_trained_draw_id or 0
    q = (
        select(models.Draw)
        .where(models.Draw.id > last_seen)
        .order_by(models.Draw.id.asc())
    )
    new_draws = list(db.scalars(q))

    if not new_draws:
        persistence.save(state_row, params)
        return {"trained": 0, "calibrated": 0, "version": params.version}

    calibrated = 0
    for i, d in enumerate(new_draws, start=1):
        res = train_step(params, d.red_balls, d.blue_ball)
        _log_train(db, state_row, d.id, res)

        if i % calibrate_every == 0:
            recent = _recent_draws(db, limit=CALIBRATION_WINDOW)
            cal = calibrate(params, recent)
            if cal is not None:
                _log_calibrate(db, state_row, params, cal)
                calibrated += 1

        state_row.last_trained_draw_id = d.id

    persistence.save(state_row, params)
    return {"trained": len(new_draws), "calibrated": calibrated, "version": params.version}


def _recent_draws(db: Session, limit: int) -> list[tuple[list[int], int]]:
    rows = db.scalars(
        select(models.Draw).order_by(desc(models.Draw.id)).limit(limit)
    ).all()
    return [(r.red_balls, r.blue_ball) for r in rows]


def predict_with_model(db: Session, count: int, seed: int | None = None):
    _, params = persistence.load_or_init(db)
    return sample_predictions(params, count=count, seed=seed)


def train_temp_model_on(
    draws: list[tuple[list[int], int]],
    prior_strength: float = 1.0,
    calibrate_every: int = 5,
) -> ModelParams:
    """构建一个**不持久化**的临时模型，按顺序学完给定 draws。

    用于 backtest：以「目标期之前的数据」从零训练一个模型，
    然后用它来预测目标期。这样不会污染主模型的状态。
    """
    params = ModelParams.fresh(prior_strength=prior_strength)
    for i, (reds, blue) in enumerate(draws, start=1):
        train_step(params, reds, blue)
        if i % calibrate_every == 0 and i >= 10:
            window = draws[max(0, i - CALIBRATION_WINDOW): i]
            calibrate(params, window)
    return params


def sample_from_params(params: ModelParams, count: int, seed: int | None = None):
    return sample_predictions(params, count=count, seed=seed)


def mark_stale_and_retrain(db: Session) -> dict:
    """供「编辑/删除历史数据」之后调用：清空模型并重训。"""
    state_row, _ = persistence.load_or_init(db)
    persistence.reset(state_row)
    _log_reset(db, state_row)
    return train_on_new_draws(db, full_retrain=False)


def reset_model(db: Session, prior_strength: float | None = None) -> ModelParams:
    state_row, _ = persistence.load_or_init(db)
    params = persistence.reset(state_row, prior_strength=prior_strength)
    _log_reset(db, state_row)
    return params


def get_state_snapshot(db: Session) -> dict:
    state_row, params = persistence.load_or_init(db)
    return {
        "name": state_row.name,
        "version": params.version,
        "temperature": params.temperature,
        "learning_rate": params.learning_rate,
        "decay": params.decay,
        "prior_strength": state_row.prior_strength,
        "last_trained_draw_id": state_row.last_trained_draw_id,
        "red_alpha": params.red_alpha.tolist(),
        "blue_alpha": params.blue_alpha.tolist(),
        "red_probs": params.red_probs().tolist(),
        "blue_probs": params.blue_probs().tolist(),
        "updated_at": state_row.updated_at.isoformat() if state_row.updated_at else None,
    }


def list_events(db: Session, limit: int = 500) -> list[models.ModelTrainingEvent]:
    state_row, _ = persistence.load_or_init(db)
    rows = db.scalars(
        select(models.ModelTrainingEvent)
        .where(models.ModelTrainingEvent.model_state_id == state_row.id)
        .order_by(models.ModelTrainingEvent.id.asc())
        .limit(limit)
    ).all()
    return list(rows)

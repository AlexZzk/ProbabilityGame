"""把内存中的 ModelParams 和数据库行互相搬运。"""
from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from .model import ModelParams

DEFAULT_MODEL_NAME = "default"


def load_or_init(db: Session, name: str = DEFAULT_MODEL_NAME, prior_strength: float = 1.0) -> tuple[models.ModelState, ModelParams]:
    row = db.scalar(select(models.ModelState).where(models.ModelState.name == name))
    if row is None:
        params = ModelParams.fresh(prior_strength=prior_strength)
        row = models.ModelState(
            name=name,
            red_alpha=params.red_alpha.tolist(),
            blue_alpha=params.blue_alpha.tolist(),
            temperature=params.temperature,
            learning_rate=params.learning_rate,
            decay=params.decay,
            prior_strength=prior_strength,
            version=0,
            last_trained_draw_id=None,
        )
        db.add(row)
        db.flush()
        return row, params
    params = _row_to_params(row)
    return row, params


def _row_to_params(row: models.ModelState) -> ModelParams:
    return ModelParams(
        red_alpha=np.array(row.red_alpha, dtype=float),
        blue_alpha=np.array(row.blue_alpha, dtype=float),
        temperature=row.temperature,
        learning_rate=row.learning_rate,
        decay=row.decay,
        version=row.version,
    )


def save(row: models.ModelState, params: ModelParams) -> None:
    row.red_alpha = params.red_alpha.tolist()
    row.blue_alpha = params.blue_alpha.tolist()
    row.temperature = params.temperature
    row.learning_rate = params.learning_rate
    row.decay = params.decay
    row.version = params.version


def reset(row: models.ModelState, prior_strength: float | None = None) -> ModelParams:
    if prior_strength is None:
        prior_strength = row.prior_strength
    params = ModelParams.fresh(prior_strength=prior_strength)
    save(row, params)
    row.prior_strength = prior_strength
    row.last_trained_draw_id = None
    return params

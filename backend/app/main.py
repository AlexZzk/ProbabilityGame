from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import draws, predictions

app = FastAPI(title="ProbabilityGame API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup() -> None:
    # 简化部署：直接 create_all。生产环境建议改用 Alembic。
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(draws.router)
app.include_router(predictions.router)

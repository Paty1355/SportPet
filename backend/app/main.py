import logging
from contextlib import asynccontextmanager

import openai
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

import app.models  # noqa: F401 – rejestruje modele w Base.metadata
from app.agents.diet_plan.images import IMAGE_DIR, IMAGE_URL_PREFIX
from app.agents.plan.exercises import GIF_DIR, GIF_URL_PREFIX
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

logger = logging.getLogger(__name__)


def _add_user_profile_columns() -> None:
    # create_all nie dodaje kolumn do istniejącej tabeli users (brak Alembica) – dokładamy je idempotentnie.
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        double = "DOUBLE PRECISION"
        columns = {
            "sex": "VARCHAR(1)",
            "birth_date": "DATE",
            "weight_kg": double,
            "height_cm": double,
            "share_pet": "BOOLEAN NOT NULL DEFAULT TRUE",
        }
        for col, typ in columns.items():
            conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {typ}"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Na hackathon wystarczy create_all; przy zmianach schematu warto dodać Alembic.
    Base.metadata.create_all(bind=engine)
    _add_user_profile_columns()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.mount(GIF_URL_PREFIX, StaticFiles(directory=GIF_DIR), name="exercises")
app.mount(IMAGE_URL_PREFIX, StaticFiles(directory=IMAGE_DIR), name="meals")


@app.exception_handler(openai.APIError)
async def llm_error_handler(_: Request, exc: openai.APIError):
    logger.exception("Azure OpenAI request failed", exc_info=exc)
    return JSONResponse(status_code=502, content={"detail": "Model provider error, try again later"})


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}

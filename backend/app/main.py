import logging
from contextlib import asynccontextmanager

import openai
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401 – rejestruje modele w Base.metadata
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.migrate import initialize_database

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Zakładamy tabele i aktualizujemy istniejący schemat przed przyjęciem żądań.
    initialize_database()
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


@app.exception_handler(openai.APIError)
async def llm_error_handler(_: Request, exc: openai.APIError):
    logger.exception("Azure OpenAI request failed", exc_info=exc)
    return JSONResponse(status_code=502, content={"detail": "Model provider error, try again later"})


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}

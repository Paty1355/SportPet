import hashlib

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.agents.diet.agent import DietAgent, get_diet_agent
from app.agents.diet_plan.agent import DietPlanAgent, get_diet_plan_agent
from app.agents.llm import StubLLM
from app.agents.photo.agent import PhotoAgent, get_photo_agent
from app.agents.plan.agent import PlanAgent, get_plan_agent
from app.agents.training.agent import TrainingAgent, get_training_agent
from app.core.azure import get_azure_client
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.memory.chroma_client import get_chroma
from app.memory.embeddings import AzureEmbeddingFunction


def _fake_embed(self, input):
    # Deterministic: identical texts get identical vectors
    digests = (hashlib.sha256(text.encode()).digest()[:16] for text in input)
    return [np.frombuffer(d, dtype=np.uint8).astype(np.float32) for d in digests]


@pytest.fixture
def chroma(tmp_path, monkeypatch):
    # Chroma in a temp dir; fake Azure credentials + fake embeddings, so tests never hit the network
    monkeypatch.setattr(settings, "chroma_path", str(tmp_path / "chroma"))
    monkeypatch.setattr(settings, "chroma_host", None)
    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://test.openai.azure.com/")
    monkeypatch.setattr(settings, "azure_openai_api_key", "test-key")
    monkeypatch.setattr(AzureEmbeddingFunction, "__call__", _fake_embed)
    get_chroma.cache_clear()
    get_azure_client.cache_clear()
    yield
    get_azure_client.cache_clear()


@pytest.fixture
def client(chroma, tmp_path, monkeypatch):
    # In-memory SQLite instead of Postgres, uploads in a temp dir
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "diet_plan_dir", str(tmp_path / "diet_plans"))
    monkeypatch.setattr(settings, "training_plan_dir", str(tmp_path / "training_plans"))
    monkeypatch.setattr(settings, "jwt_secret", "test-secret-that-is-at-least-32-bytes-long")

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_photo_agent] = lambda: PhotoAgent(StubLLM())
    app.dependency_overrides[get_training_agent] = lambda: TrainingAgent(StubLLM())
    app.dependency_overrides[get_diet_agent] = lambda: DietAgent(StubLLM())
    app.dependency_overrides[get_diet_plan_agent] = lambda: DietPlanAgent(StubLLM())
    app.dependency_overrides[get_plan_agent] = lambda: PlanAgent(StubLLM())
    # No `with` – lifespan (create_all on Postgres) does not run
    yield TestClient(app)
    app.dependency_overrides.clear()


QUESTIONNAIRE_ANSWERS = [
    "3",
    "returning",
    "glutes, core",
    "1,2",
    "burpees; jumping",
    "back, diastasis",
    "mwf",
    "60",
    "active",
    "cautious",
]


@pytest.fixture
def complete_questionnaire(client):
    def complete(headers):
        for answer in QUESTIONNAIRE_ANSWERS:
            res = client.post("/api/v1/agents/training/chat", json={"message": answer}, headers=headers)
            assert res.status_code == 200, res.text
        return res

    return complete


@pytest.fixture
def auth_headers(client):
    client.post("/api/v1/auth/register", json={"email": "test@example.com", "password": "password123"})
    res = client.post("/api/v1/auth/login", data={"username": "test@example.com", "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.agents.llm import StubLLM
from app.agents.photo.agent import PhotoAgent, get_photo_agent
from app.agents.training.agent import TrainingAgent, get_training_agent
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.memory.chroma_client import get_chroma


@pytest.fixture
def client(tmp_path, monkeypatch):
    # SQLite w pamięci zamiast Postgresa, Chroma i uploady w katalogu tymczasowym
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(settings, "chroma_path", str(tmp_path / "chroma"))
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "jwt_secret", "test-secret-that-is-at-least-32-bytes-long")
    # Testy nigdy nie wołają Azure, nawet jeśli klucze są w .env
    monkeypatch.setattr(settings, "azure_openai_endpoint", None)
    monkeypatch.setattr(settings, "azure_openai_api_key", None)
    get_chroma.cache_clear()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_photo_agent] = lambda: PhotoAgent(StubLLM())
    app.dependency_overrides[get_training_agent] = lambda: TrainingAgent(StubLLM())
    # Bez `with` – lifespan (create_all na Postgresie) się nie uruchamia
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    client.post("/api/v1/auth/register", json={"email": "test@example.com", "password": "password123"})
    res = client.post("/api/v1/auth/login", data={"username": "test@example.com", "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

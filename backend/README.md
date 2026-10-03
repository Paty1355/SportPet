# HackYeah Backend

FastAPI backend: JWT auth, users (Postgres), photo & training agents (Azure OpenAI) with Chroma memory and a RAG knowledge base.

## Requirements

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Docker (Postgres + Chroma)
- Azure OpenAI resource (chat + embedding deployments) – without it chat falls back to a stub LLM, but memory/RAG won't work

## Quick start (local dev)

All commands from `backend/` unless stated otherwise.

```bash
# 1. Config – then fill in JWT_SECRET and AZURE_OPENAI_* in .env
cp .env.example .env

# 2. Install dependencies (incl. dev tools: pytest, ruff)
uv sync

# 3. Start Postgres + Chroma (from repo root)
docker compose up -d db chroma

# 4. Load RAG documents into Chroma (once – see "RAG knowledge base")
uv run python -m app.rag.ingest

# 5. Run the API
uv run uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Full stack in Docker

From repo root:

```bash
docker compose up -d --build
```

| Service   | Host port | Notes                                   |
|-----------|-----------|-----------------------------------------|
| `backend` | 8000      | reads `backend/.env`                    |
| `db`      | 5432      | Postgres 16, volume `pgdata`            |
| `chroma`  | 8001      | Chroma server, volume `chroma_data`     |

Inside compose the backend talks to `db:5432` and `chroma:8000` – these are set in `docker-compose.yml` and override `.env`.

## Configuration

See [`.env.example`](.env.example). Most important:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres connection string |
| `JWT_SECRET` | generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `CHROMA_HOST` / `CHROMA_PORT` | Chroma server in Docker (`localhost` / `8001` locally) |
| `AZURE_OPENAI_*` | endpoint, key and **deployment names** (not model names) from Azure AI Foundry |

## RAG knowledge base

Source documents (PDF/TXT) live in [`docs_RAG/`](docs_RAG/).

```bash
# Dry run – show how files are chunked, nothing is stored
uv run python -m app.rag.chunking

# Chunk + embed + store in Chroma (collection "training")
uv run python -m app.rag.ingest

# Drop the collection and rebuild from scratch
uv run python -m app.rag.ingest --reset

# Options: --dir, --name, --chunk-size (default 1000), --overlap (default 200)
uv run python -m app.rag.ingest --help
```

Re-ingesting a file overwrites its chunks (no duplicates). Run ingest again when:
- you add or change files in `docs_RAG/`,
- the Chroma volume was removed (`docker compose down -v`),
- you change the embedding deployment (collection names include the embedding tag, so a new, empty collection is used).

Diet agent documents live in [`docs_RAG_diet/`](docs_RAG_diet/); ingest with `uv run python -m app.rag.ingest --dir docs_RAG_diet --name diet`.

Chroma data persists in the `chroma_data` volume across restarts and rebuilds.

## API

All endpoints under `/api/v1`; everything except auth requires `Authorization: Bearer <token>`.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | create account |
| POST | `/auth/login` | get JWT (form: `username`, `password`) |
| GET / PATCH | `/users/me` | current user |
| POST | `/agents/photo` | photo agent |
| GET | `/agents/photo/history` | photo agent history |
| POST | `/agents/training/chat` | training agent chat |
| GET | `/agents/training/history` | training agent history |
| POST | `/agents/diet/chat` | diet agent chat (see [`app/agents/diet/README.md`](app/agents/diet/README.md)) |
| GET | `/agents/diet/history` | diet agent history |
| GET / DELETE | `/agents/diet/questionnaire` | diet questionnaire status / reset |

## Tests & linting

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

Tests use in-memory SQLite, a temp embedded Chroma and fake embeddings – no Docker or Azure needed.

## Project structure

```
app/
  api/v1/     # routers
  agents/     # photo & training agents, LLM wrapper
  core/       # config, security, Azure client, deps
  db/         # SQLAlchemy engine/session
  memory/     # Chroma client, embeddings, per-user memory
  models/     # ORM models
  rag/        # chunking, knowledge base, ingest CLI
  schemas/    # Pydantic schemas
  services/   # business logic
  storage/    # file uploads
docs_RAG/     # RAG source documents (training)
docs_RAG_diet/ # RAG source documents (diet)
tests/
```
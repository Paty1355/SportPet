# HackYeah Backend

FastAPI backend: JWT auth, users (Postgres), photo & training agents with Chroma memory, plus a VisionAgent for gym-machine photos backed by Azure OpenAI and a dedicated RAG collection.

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
| `backend` | 8002      | reads `backend/.env`                    |
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

All endpoints under `/api/v1`; auth and VisionAgent analyze are public. Other endpoints require `Authorization: Bearer <token>`.

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
| POST | `/agents/vision/analyze` | classify a machine photo and get usage instructions (public) |

## VisionAgent: machine photos

`POST /api/v1/agents/vision/analyze` accepts one gym-machine photo as multipart field `file`.
This endpoint is public and does not require a JWT. It keeps the image in memory for the request.

The pipeline is: Azure vision deployment → classification from the imported catalog →
semantic retrieval in the separate `gym_machines_<embedding_tag>` Chroma collection →
Azure text deployment → structured English usage instructions.

Configure `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_VISION_DEPLOYMENT`,
`AZURE_OPENAI_CHAT_DEPLOYMENT` and `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` in `.env`.
The vision and text deployments must support Structured Outputs, and the vision deployment must accept images.
If vision deployment is unset, the chat deployment is used for both calls.
VisionAgent uses real Azure clients; missing credentials return HTTP 503.

Machine cards live in [`docs_RAG/vision/`](docs_RAG/vision/README.md).
Only `machines.example.json` is provided initially; its values are placeholders.
Create `machines.json` with your reviewed cards before real use. Each card uses one English machine name in `name`.
The example is never imported automatically.

```bash
# Validate the example without Azure credentials or a Chroma connection
uv run python -m app.agents.vision.seed --file docs_RAG/vision/machines.example.json --dry-run

# Validate your actual cards
uv run python -m app.agents.vision.seed --dry-run

# Import actual cards (Azure and Chroma required)
uv run python -m app.agents.vision.seed

# In Docker, after adding cards and rebuilding the backend image
docker compose exec backend python -m app.agents.vision.seed
```

The default data path is resolved relative to the source module, not the current working directory.
Re-importing updates cards by `machine_id` without duplicates; cards absent from the new file are retained.
The training PDF/TXT importer does not load this folder.

```bash
curl -X POST http://localhost:8000/api/v1/agents/vision/analyze -F "file=@machine.jpg"
```

The response contains `machine_id`, `machine_name`, `category`, `description`,
`primary_muscles`, `secondary_muscles`, `setup_steps`, `exercise_steps`, `tips` and `sources`.
Machine name, ID, category and sources come from the retrieved card. `machine_name` is the card's English `name`;
usage instructions are generated in English for beginners, even when the source card uses another language:
short, direct sentences, everyday muscle names,
and one action per instruction step. The model simplifies wording while preserving the card's meaning,
sequence, safety conditions and warnings; it does not add advice absent from the card.

The usage prompt includes an explicit JSON example with exactly the six model-generated fields.
The SDK sends a strict JSON Schema and parses the response into `MachineUsage`; Pydantic rejects
missing or extra fields, wrong types, blank text and empty required lists. The backend then builds
one `VisionResponse` with the machine metadata from the retrieved card. Invalid model output returns HTTP 502.

After changing the usage prompt, rebuild the backend from the repository root:

```bash
docker compose up -d --build --force-recreate backend
```

With the current Compose configuration, Swagger is available at http://localhost:8002/docs.
A prompt-only change does not require re-importing machine cards or regenerating embeddings.

Errors: HTTP 422 for an empty upload or an unsupported machine; HTTP 503 for missing credentials
or missing knowledge; HTTP 502 for provider failures or invalid structured model responses.
The existing application startup still requires its configured Postgres database.


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
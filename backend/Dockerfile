FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml .
COPY app ./app
# Cache pip między buildami – chromadb jest ciężkie, przebudowa po zmianie kodu nie pobiera wszystkiego od nowa
RUN --mount=type=cache,target=/root/.cache/pip pip install .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

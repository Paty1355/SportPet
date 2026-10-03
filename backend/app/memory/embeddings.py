import re
from typing import Any

from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.utils.embedding_functions import register_embedding_function
from openai import AzureOpenAI

from app.core.config import settings


@register_embedding_function
class AzureEmbeddingFunction(EmbeddingFunction[Documents]):
    def __init__(self, client: AzureOpenAI, deployment: str):
        self.client = client
        self.deployment = deployment

    def __call__(self, input: Documents) -> Embeddings:
        response = self.client.embeddings.create(model=self.deployment, input=list(input))
        return [item.embedding for item in sorted(response.data, key=lambda d: d.index)]

    @staticmethod
    def name() -> str:
        return "azure_openai"

    def default_space(self) -> str:
        return "cosine"

    def get_config(self) -> dict[str, Any]:
        # Bez klucza API – config jest zapisywany przez Chromę na dysku
        return {"deployment": self.deployment}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "AzureEmbeddingFunction":
        from app.core.azure import get_azure_client

        return AzureEmbeddingFunction(get_azure_client(), config["deployment"])


def get_embedding_function() -> EmbeddingFunction | None:
    """Azure, jeśli skonfigurowany; None → domyślne lokalne embeddingi Chromy (all-MiniLM)."""
    if not settings.azure_enabled:
        return None

    from app.core.azure import get_azure_client

    return AzureEmbeddingFunction(get_azure_client(), settings.azure_openai_embedding_deployment)


def embedding_tag() -> str:
    """Sufiks nazwy kolekcji: różne modele dają wektory o różnych wymiarach, więc nie mogą dzielić kolekcji."""
    tag = settings.azure_openai_embedding_deployment if settings.azure_enabled else "local"
    return re.sub(r"[^a-zA-Z0-9_-]", "-", tag)

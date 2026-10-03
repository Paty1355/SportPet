from functools import lru_cache

from openai import AsyncAzureOpenAI, AzureOpenAI

from app.core.config import settings


def _client_kwargs() -> dict:
    if not settings.azure_enabled:
        raise RuntimeError("Azure OpenAI is not configured (AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY)")
    return {
        "azure_endpoint": settings.azure_openai_endpoint,
        "api_key": settings.azure_openai_api_key,
        "api_version": settings.azure_openai_api_version,
    }


@lru_cache
def get_async_azure_client() -> AsyncAzureOpenAI:
    """Klient asynchroniczny – chat i zdjęcia (wywoływane z endpointów FastAPI)."""
    return AsyncAzureOpenAI(**_client_kwargs())


@lru_cache
def get_azure_client() -> AzureOpenAI:
    """Klient synchroniczny – embeddingi (Chroma wywołuje funkcję embeddingów synchronicznie)."""
    return AzureOpenAI(**_client_kwargs())

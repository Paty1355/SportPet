from functools import lru_cache

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from app.core.config import settings
from app.memory.embeddings import embedding_tag, get_embedding_function


@lru_cache
def get_chroma() -> ClientAPI:
    # Lazy: Chroma is loaded on first agent use.
    if settings.chroma_host:
        return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return chromadb.PersistentClient(path=settings.chroma_path)


def get_collection(name: str) -> Collection:
    return get_chroma().get_or_create_collection(
        f"{name}_{embedding_tag()}",
        embedding_function=get_embedding_function(),
        configuration={"hnsw": {"space": "cosine"}},
    )

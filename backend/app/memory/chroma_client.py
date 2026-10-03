from functools import lru_cache

import chromadb
from chromadb.api import ClientAPI

from app.core.config import settings


@lru_cache
def get_chroma() -> ClientAPI:
    # Leniwie: Chroma (i model embeddingów) ładuje się dopiero przy pierwszym użyciu agenta.
    return chromadb.PersistentClient(path=settings.chroma_path)

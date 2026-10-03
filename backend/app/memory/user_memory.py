from datetime import UTC, datetime
from uuid import uuid4

from app.memory.chroma_client import get_chroma
from app.memory.embeddings import embedding_tag, get_embedding_function


class UserMemory:
    """Długoterminowa pamięć semantyczna agenta.

    Jedna kolekcja na agenta i model embeddingów (np. `training_memory_text-embedding-3-small`),
    wpisy rozdzielone po `user_id` w metadanych – każde wyszukiwanie jest filtrowane po użytkowniku.
    """

    def __init__(self, agent_name: str):
        embedding_function = get_embedding_function()
        kwargs = {"embedding_function": embedding_function} if embedding_function else {}
        self.collection = get_chroma().get_or_create_collection(
            f"{agent_name}_memory_{embedding_tag()}",
            configuration={"hnsw": {"space": "cosine"}},
            **kwargs,
        )

    def add(self, user_id: int, text: str, **metadata: str | int | float | bool) -> None:
        self.collection.add(
            ids=[uuid4().hex],
            documents=[text],
            metadatas=[{"user_id": user_id, "created_at": datetime.now(UTC).isoformat(), **metadata}],
        )

    def search(self, user_id: int, query: str, k: int = 5) -> list[str]:
        if self.collection.count() == 0:
            return []
        result = self.collection.query(query_texts=[query], n_results=k, where={"user_id": user_id})
        documents = result.get("documents") or [[]]
        return documents[0]

    def clear(self, user_id: int) -> None:
        self.collection.delete(where={"user_id": user_id})

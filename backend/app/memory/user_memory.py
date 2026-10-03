from datetime import UTC, datetime
from uuid import uuid4

from app.memory.chroma_client import get_collection


class UserMemory:
    """Long-term semantic memory of an agent.

    One collection per agent and embedding model (e.g. `training_memory_text-embedding-3-small`);
    entries are scoped by `user_id` metadata and every search filters on it.
    """

    def __init__(self, agent_name: str):
        self.collection = get_collection(f"{agent_name}_memory")

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

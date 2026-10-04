from itertools import batched

from app.memory.chroma_client import get_chroma, get_collection
from app.schemas.rag import Chunk, RetrievedChunk


class KnowledgeBase:

    batch_size = 100

    def __init__(self, name: str):
        self.name = f"{name}_docs"
        self.collection = get_collection(self.name)

    def add_chunks(self, chunks: list[Chunk]) -> None:
        for batch in batched(chunks, self.batch_size):
            self.collection.upsert(
                ids=[f"{c.source}:{c.chunk_index}" for c in batch],
                documents=[c.text for c in batch],
                metadatas=[self._metadata(c) for c in batch],
            )

    def search(self, query: str, k: int = 5) -> list[RetrievedChunk]:
        if self.collection.count() == 0:
            return []
        result = self.collection.query(
            query_texts=[query], n_results=k, include=["documents", "metadatas", "distances"]
        )
        return [
            RetrievedChunk(text=doc, source=meta["source"], page=meta.get("page"), score=1 - dist)
            for doc, meta, dist in zip(
                result["documents"][0], result["metadatas"][0], result["distances"][0], strict=True
            )
        ]

    def delete_source(self, source: str) -> None:
        self.collection.delete(where={"source": source})

    def count(self) -> int:
        return self.collection.count()

    def reset(self) -> None:
        get_chroma().delete_collection(self.collection.name)
        self.collection = get_collection(self.name)

    @staticmethod
    def _metadata(chunk: Chunk) -> dict[str, str | int]:
        metadata: dict[str, str | int] = {"source": chunk.source, "chunk_index": chunk.chunk_index}
        if chunk.page is not None:
            metadata["page"] = chunk.page
        return metadata

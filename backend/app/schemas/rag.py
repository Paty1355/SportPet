from pydantic import BaseModel, Field


class PageText(BaseModel):
    page: int | None = None  # None for files without pages (txt)
    text: str


class Chunk(BaseModel):
    text: str = Field(min_length=1)
    source: str
    page: int | None = None
    chunk_index: int = Field(ge=0)


class RetrievedChunk(BaseModel):
    text: str
    source: str
    page: int | None = None
    score: float  # cosine similarity, higher is better

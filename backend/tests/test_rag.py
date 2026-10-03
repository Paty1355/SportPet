from app.rag.chunking import DocumentChunker
from app.rag.knowledge_base import KnowledgeBase
from app.schemas.rag import Chunk


def test_chunks_respect_size_and_overlap():
    text = " ".join(f"Sentence number {i} about squats." for i in range(50))
    chunks = DocumentChunker(chunk_size=100, overlap=30).chunk_text(text)

    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)
    assert all(b[:10] in a for a, b in zip(chunks, chunks[1:], strict=False))


def test_clean_joins_hyphenated_and_wrapped_lines():
    assert DocumentChunker.clean("Bench pre-\nss  is\ngreat.\n\n\nNext") == "Bench press is great.\n\nNext"


def test_txt_falls_back_to_cp1250(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("Przysiad głęboki.\n\nPlecy proste.", encoding="cp1250")

    chunks = DocumentChunker().process_file(path)

    assert chunks[0].text == "Przysiad głęboki.\n\nPlecy proste."
    assert (chunks[0].source, chunks[0].page) == ("notes.txt", None)


def test_knowledge_base_upsert_is_idempotent_and_searchable(chroma):
    kb = KnowledgeBase("test")
    chunks = [Chunk(text=f"Exercise {i}", source="book.pdf", page=i + 1, chunk_index=i) for i in range(3)]

    kb.add_chunks(chunks)
    kb.add_chunks(chunks)

    assert kb.count() == 3
    top = kb.search("Exercise 1", k=1)[0]
    assert (top.source, top.page) == ("book.pdf", 2)


def test_knowledge_base_delete_source(chroma):
    kb = KnowledgeBase("test")
    kb.add_chunks([Chunk(text="a", source="a.txt", chunk_index=0), Chunk(text="b", source="b.txt", chunk_index=0)])

    kb.delete_source("a.txt")

    assert kb.count() == 1
    assert kb.search("b")[0].source == "b.txt"

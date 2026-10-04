import argparse
import logging
from pathlib import Path

from app.rag.chunking import DocumentChunker
from app.rag.knowledge_base import KnowledgeBase


def main() -> None:
    parser = argparse.ArgumentParser(description="Load PDF/TXT files, chunk them and store them in Chroma.")
    parser.add_argument("--dir", type=Path, default=Path("docs_RAG"))
    parser.add_argument("--name", default="training", help="knowledge base name (agent)")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--overlap", type=int, default=200)
    parser.add_argument("--reset", action="store_true", help="drop the whole collection first")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    chunker = DocumentChunker(args.chunk_size, args.overlap)
    kb = KnowledgeBase(args.name)
    if args.reset:
        kb.reset()

    for path in sorted(args.dir.iterdir()):
        if path.suffix.lower() not in chunker.SUPPORTED_EXTENSIONS:
            continue
        chunks = chunker.process_file(path)
        kb.delete_source(path.name)
        kb.add_chunks(chunks)
        print(f"{path.name}: {len(chunks)} chunks")

    print(f"\n{kb.collection.name}: {kb.count()} chunks total")


if __name__ == "__main__":
    main()

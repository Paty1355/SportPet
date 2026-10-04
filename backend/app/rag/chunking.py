import argparse
import logging
import re
from pathlib import Path

from pypdf import PdfReader

from app.schemas.rag import Chunk, PageText

logger = logging.getLogger(__name__)


class DocumentChunker:
    SUPPORTED_EXTENSIONS = {".pdf", ".txt"}
    SEPARATORS = ["\n\n", "\n", ". ", " "]

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        if not 0 <= overlap < chunk_size:
            raise ValueError("overlap must be in [0, chunk_size)")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def load(self, path: Path) -> list[PageText]:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            pages = [
                PageText(page=i, text=text)
                for i, page in enumerate(PdfReader(path).pages, start=1)
                if (text := self.clean(page.extract_text() or ""))
            ]
            if not pages:
                logger.warning("%s: no text layer (scanned?), skipping", path.name)
            return pages
        if suffix == ".txt":
            try:
                raw = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                raw = path.read_text(encoding="cp1250")
            text = self.clean(raw)
            return [PageText(text=text)] if text else []
        raise ValueError(f"Unsupported format: {path.suffix}")

    @staticmethod
    def clean(text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def chunk_text(self, text: str) -> list[str]:
        chunks: list[str] = []
        current = ""
        for piece in self._split(text, self.SEPARATORS):
            if current and len(current) + len(piece) > self.chunk_size:
                chunks.append(current.strip())
                current = self._tail(current, min(self.overlap, self.chunk_size - len(piece)))
            current += piece
        if current.strip():
            chunks.append(current.strip())
        return chunks

    def process_file(self, path: Path) -> list[Chunk]:
        chunks: list[Chunk] = []
        for page in self.load(path):
            for text in self.chunk_text(page.text):
                chunks.append(Chunk(text=text, source=path.name, page=page.page, chunk_index=len(chunks)))
        return chunks

    def process_directory(self, directory: Path) -> list[Chunk]:
        chunks: list[Chunk] = []
        for path in sorted(directory.iterdir()):
            if path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                chunks.extend(self.process_file(path))
        return chunks

    def _split(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]
        if not separators:
            return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]
        sep, rest = separators[0], separators[1:]
        if sep not in text:
            return self._split(text, rest)
        pieces = text.split(sep)
        pieces = [p + sep for p in pieces[:-1]] + [pieces[-1]]
        return [part for piece in pieces if piece for part in self._split(piece, rest)]

    @staticmethod
    def _tail(text: str, n: int) -> str:
        if n <= 0:
            return ""
        if len(text) <= n:
            return text
        tail = text[-n:]
        cut = tail.find(" ")
        return tail[cut + 1 :] if cut != -1 else tail


def main() -> None:
    parser = argparse.ArgumentParser(description="Load PDF/TXT files and split them into chunks (dry run).")
    parser.add_argument("--dir", type=Path, default=Path("docs_RAG"))
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--overlap", type=int, default=200)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    chunker = DocumentChunker(args.chunk_size, args.overlap)
    total = 0
    for path in sorted(args.dir.iterdir()):
        if path.suffix.lower() not in chunker.SUPPORTED_EXTENSIONS:
            continue
        chunks = chunker.process_file(path)
        total += len(chunks)
        pages = len({c.page for c in chunks})
        print(f"{path.name}: {pages} pages with text, {len(chunks)} chunks")
        if chunks:
            print(f"  > {chunks[0].text[:150]!r}")
    print(f"\nTotal: {total} chunks")


if __name__ == "__main__":
    main()

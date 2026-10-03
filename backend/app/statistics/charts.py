from io import BytesIO
from typing import BinaryIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Message


def analyze(db: Session, user_id: int, limit: int = 200) -> dict[str, object]:
    base = select(Message).where(Message.user_id == user_id).order_by(Message.id.desc()).limit(limit).subquery()

    total_messages = db.scalar(select(func.count(base.c.id))) or 0
    per_agent_rows = db.execute(
        select(base.c.agent, func.count(base.c.id)).group_by(base.c.agent).order_by(base.c.agent)
    ).all()

    return {
        "total_messages": int(total_messages),
        "per_agent": [{"agent": agent, "count": int(count)} for agent, count in per_agent_rows],
    }


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf_bytes(lines: list[str]) -> bytes:
    escaped = [_escape_pdf_text(line) for line in lines]
    content = "BT\n/F1 12 Tf\n72 770 Td\n"
    text_rows = []
    for idx, line in enumerate(escaped):
        if idx == 0:
            text_rows.append(f"({line}) Tj")
        else:
            text_rows.append(f"0 -18 Td\n({line}) Tj")
    content += "\n".join(text_rows)
    content += "\nET\n"
    content_bytes = content.encode("utf-8")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources"
            b" << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        ),
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        f"5 0 obj << /Length {len(content_bytes)} >> stream\n".encode() + content_bytes + b"endstream\nendobj\n",
    ]

    buffer = BytesIO()
    buffer.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(buffer.tell())
        buffer.write(obj)

    xref_offset = buffer.tell()
    buffer.write(f"xref\n0 {len(offsets)}\n".encode())
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.write(f"{offset:010d} 00000 n \n".encode())

    trailer = f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    buffer.write(trailer.encode())
    return buffer.getvalue()


def render_pdf(result: dict[str, object], dest: BinaryIO) -> None:
    per_agent = result.get("per_agent", [])
    lines = ["Raport aktywności użytkownika", f"Łączna liczba wiadomości: {result.get('total_messages', 0)}"]
    if isinstance(per_agent, list) and per_agent:
        lines.append("Wiadomości per agent:")
        for item in per_agent:
            if isinstance(item, dict):
                lines.append(f"- {item.get('agent', 'unknown')}: {item.get('count', 0)}")

    dest.write(_build_pdf_bytes(lines))

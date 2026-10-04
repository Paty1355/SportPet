from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Message(Base):
    """Dosłowna historia rozmów z agentami (pamięć krótkoterminowa)."""

    __tablename__ = "messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["post_workout_checkin_id", "user_id"],
            ["post_workout_checkins.id", "post_workout_checkins.user_id"],
            name="fk_messages_post_workout_owner",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "post_workout_checkin_id IS NULL OR agent = 'post_workout'", name="ck_messages_post_workout_agent"
        ),
        Index("ix_messages_post_workout_session", "user_id", "post_workout_checkin_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    agent: Mapped[str] = mapped_column(String(32), index=True)  # "photo" | "training" | "post_workout"
    post_workout_checkin_id: Mapped[str | None] = mapped_column(String(36))
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

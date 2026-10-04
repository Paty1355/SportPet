from sqlalchemy import ForeignKey, String, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON
from datetime import datetime
from app.db.base import Base


class Friendship(Base):
    __tablename__ = "friendships"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    addressee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending") # "pending", "accepted"
    
    __table_args__ = (
        UniqueConstraint("requester_id", "addressee_id", name="uix_friendship"),
    )

class PetProfile(Base):
    __tablename__ = "pet_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    level: Mapped[int] = mapped_column(default=1)
    hat: Mapped[str | None] = mapped_column(String(50))
    body: Mapped[str | None] = mapped_column(String(50))
    background: Mapped[str | None] = mapped_column(String(50))
    decor: Mapped[list | None] = mapped_column(JSON)
    theme: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
from datetime import datetime

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QuestionnaireState(Base):

    __tablename__ = "training_questionnaires"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    step: Mapped[int] = mapped_column(default=0)
    answers: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    completed_at: Mapped[datetime | None]


class DietQuestionnaireState(Base):

    __tablename__ = "diet_questionnaires"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    step: Mapped[int] = mapped_column(default=0)
    answers: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    completed_at: Mapped[datetime | None]

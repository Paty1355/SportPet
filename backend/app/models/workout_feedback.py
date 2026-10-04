from datetime import datetime

from sqlalchemy import ForeignKey, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkoutFeedback(Base):

    __tablename__ = "workout_feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    fatigue_level: Mapped[int] = mapped_column(SmallInteger)
    feeling_trend: Mapped[str] = mapped_column(String(16))
    motivation_level: Mapped[int] = mapped_column(SmallInteger)
    pain_experienced: Mapped[str] = mapped_column(String(16))
    perceived_exertion_rating: Mapped[int] = mapped_column(SmallInteger)
    reporting_frequency: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PostWorkoutCheckIn(Base):
    __tablename__ = "post_workout_checkins"
    __table_args__ = (
        UniqueConstraint("user_id", "request_id", name="uq_post_workout_start_request"),
        UniqueConstraint("id", "user_id", name="uq_post_workout_checkin_owner"),
        Index("ix_post_workout_checkins_user_workout", "user_id", "workout_ended_at"),
        CheckConstraint("version >= 0", name="ck_post_workout_version"),
        CheckConstraint(
            "status IN ('in_progress', 'awaiting_confirmation', 'completed', 'interrupted')",
            name="ck_post_workout_status",
        ),
        *(
            CheckConstraint(f"{column} BETWEEN 0 AND 10", name=f"ck_post_workout_{column}")
            for column in (
                "fatigue_level",
                "mood_level",
                "motivation_level",
                "perceived_exertion_rating",
                "pain_intensity",
            )
        ),
        CheckConstraint("feeling_change IN ('better', 'same', 'worse')", name="ck_post_workout_feeling"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[str] = mapped_column(String(36))
    start_payload_hash: Mapped[str] = mapped_column(String(64))
    workout_ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    workout_type: Mapped[str | None] = mapped_column(String(80))
    workout_duration_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(32), default="in_progress")
    version: Mapped[int] = mapped_column(default=0)
    answers: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    processed_requests: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    safety_observations: Mapped[list[dict]] = mapped_column(JSON, default=list)
    fatigue_level: Mapped[int | None] = mapped_column(SmallInteger)
    feeling_change: Mapped[str | None] = mapped_column(String(16))
    mood_level: Mapped[int | None] = mapped_column(SmallInteger)
    motivation_level: Mapped[int | None] = mapped_column(SmallInteger)
    perceived_exertion_rating: Mapped[int | None] = mapped_column(SmallInteger)
    pain_experienced: Mapped[bool | None]
    pain_intensity: Mapped[int | None] = mapped_column(SmallInteger)
    pain_locations: Mapped[list[str]] = mapped_column(JSON, default=list)
    pain_description: Mapped[str | None] = mapped_column(Text)
    support: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PostWorkoutReport(Base):
    __tablename__ = "post_workout_reports"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "period", "timezone", "period_start", "snapshot_hash", name="uq_post_workout_report_snapshot"
        ),
        Index("ix_post_workout_reports_user_created", "user_id", "computed_at"),
        CheckConstraint("period IN ('daily', 'weekly', 'monthly')", name="ck_post_workout_report_period"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String(16))
    timezone: Mapped[str] = mapped_column(String(64))
    period_start: Mapped[date]
    period_end: Mapped[date]
    is_partial: Mapped[bool]
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    analysis_version: Mapped[str] = mapped_column(String(16), default="1")
    statistics: Mapped[dict] = mapped_column(JSON)
    support: Mapped[dict | None] = mapped_column(JSON)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "post_workout_reporting_frequency IN ('daily', 'weekly', 'monthly')",
            name="ck_users_post_workout_frequency",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True)
    # Profil zdrowotny (opcjonalny). Wiek liczymy z birth_date przy odczycie.
    sex: Mapped[str | None] = mapped_column(String(1))  # "F" | "M"
    birth_date: Mapped[date | None]
    weight_kg: Mapped[float | None] = mapped_column(Float)
    height_cm: Mapped[float | None] = mapped_column(Float)
    post_workout_reporting_frequency: Mapped[str] = mapped_column(String(16), default="weekly", server_default="weekly")
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Warsaw", server_default="Europe/Warsaw")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

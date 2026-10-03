from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_user_fk = lambda **kw: mapped_column(ForeignKey("users.id", ondelete="CASCADE"), **kw)  # noqa: E731


class VitalSample(Base):
    """Skalarny szereg czasowy. Nowa metryka = nowa wartość `metric`, bez migracji."""

    __tablename__ = "vital_samples"

    user_id: Mapped[int] = _user_fk(primary_key=True)
    metric: Mapped[str] = mapped_column(String(32), primary_key=True)  # heart_rate | spo2 | stress
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    value: Mapped[float] = mapped_column(Float)


class DailySummary(Base):
    """Jedna wartość na dzień. Nowa dzienna metryka = nowa kolumna."""

    __tablename__ = "daily_summaries"

    user_id: Mapped[int] = _user_fk(primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    steps: Mapped[int | None]
    sleep_minutes: Mapped[int | None]


class BloodPressureReading(Base):
    """Skurczowe i rozkurczowe to jedno zdarzenie, więc osobny wiersz, nie dwie próbki."""

    __tablename__ = "blood_pressure_readings"
    __table_args__ = (UniqueConstraint("user_id", "ts"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = _user_fk(index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    systolic: Mapped[int] = mapped_column(SmallInteger)
    diastolic: Mapped[int] = mapped_column(SmallInteger)


class EcgRecording(Base):
    __tablename__ = "ecg_recordings"
    __table_args__ = (UniqueConstraint("user_id", "started_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = _user_fk(index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sample_rate_hz: Mapped[int] = mapped_column(SmallInteger)
    avg_heart_rate: Mapped[float] = mapped_column(Float)
    classification: Mapped[str] = mapped_column(String(32))
    # JSON, nie ARRAY: testy backendu idą na SQLite
    samples: Mapped[list[float]] = mapped_column(JSON)


class CycleDay(Base):
    """Tylko dla sex == "F"."""

    __tablename__ = "cycle_days"

    user_id: Mapped[int] = _user_fk(primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    cycle_day: Mapped[int] = mapped_column(SmallInteger)
    phase: Mapped[str] = mapped_column(String(16))  # menstrual | follicular | ovulation | luteal
    cycle_length: Mapped[int] = mapped_column(SmallInteger)

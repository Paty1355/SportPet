"""Health data reads for charts. Always the logged-in user's data (JWT)."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models import BloodPressureReading, CycleDay, DailySummary, EcgRecording, VitalSample
from app.schemas.health import (
    Dashboard,
    EcgSummary,
    LatestValue,
    SeriesOut,
    SeriesPoint,
)
from app.statistics import analyze

router = APIRouter(prefix="/health", tags=["health-charts"])

UNITS = {"heart_rate": "bpm", "spo2": "%", "stress": "score 0-100"}
BUCKET_SECONDS = {"raw": 0, "5m": 300, "15m": 900, "1h": 3600, "1d": 86400}
MAX_RANGE_DAYS = 60
MAX_RAW_RANGE_DAYS = 3  # raw is ~864 points/day/metric; longer ranges should go through a bucket


def _utc(dt: datetime) -> datetime:
    # SQLite oddaje naive, Postgres aware; wszystko trzymamy w UTC
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def _range(start: datetime | None, end: datetime | None, default_days: int, max_days: int = MAX_RANGE_DAYS):
    end = _utc(end) if end else datetime.now(UTC)
    start = _utc(start) if start else end - timedelta(days=default_days)
    if start >= end:
        raise HTTPException(422, "start must be before end")
    if end - start > timedelta(days=max_days):
        raise HTTPException(422, f"Range too long (max {max_days} days)")
    return start, end


def _date_range(start: date | None, end: date | None, default_days: int):
    end = end or datetime.now(UTC).date()
    start = start or end - timedelta(days=default_days - 1)
    if start > end:
        raise HTTPException(422, "start must not be after end")
    if (end - start).days > MAX_RANGE_DAYS:
        raise HTTPException(422, f"Range too long (max {MAX_RANGE_DAYS} days)")
    return start, end


StartDT = Annotated[datetime | None, Query(description="ISO 8601 (with timezone). Default end − 24 h")]
EndDT = Annotated[datetime | None, Query(description="ISO 8601 (with timezone). Default now")]
EndD = Annotated[date | None, Query(description="YYYY-MM-DD, inclusive. Default today (UTC)")]


@router.get("/series", response_model=SeriesOut)
def series(
    user: CurrentUser,
    db: DbSession,
    metric: Literal["heart_rate", "spo2", "stress"],
    start: StartDT = None,
    end: EndDT = None,
    bucket: Literal["raw", "5m", "15m", "1h", "1d"] = "raw",
):
    """Time series. bucket != raw returns the mean (`value`) and `min`/`max` within the interval (UTC)."""
    start, end = _range(start, end, default_days=1)
    if bucket == "raw" and end - start > timedelta(days=MAX_RAW_RANGE_DAYS):
        raise HTTPException(422, f"bucket=raw allows at most {MAX_RAW_RANGE_DAYS} days; use bucket=5m/15m/1h/1d")
    rows = db.execute(
        select(VitalSample.ts, VitalSample.value)
        .where(
            VitalSample.user_id == user.id,
            VitalSample.metric == metric,
            VitalSample.ts >= start,
            VitalSample.ts < end,
        )
        .order_by(VitalSample.ts)
    ).all()

    size = BUCKET_SECONDS[bucket]
    if size == 0:
        points = [SeriesPoint(ts=_utc(ts), value=value) for ts, value in rows]
    else:
        groups: dict[int, list[float]] = {}
        for ts, value in rows:
            groups.setdefault(int(_utc(ts).timestamp()) // size, []).append(value)
        points = [
            SeriesPoint(
                ts=datetime.fromtimestamp(key * size, UTC),
                value=round(sum(vals) / len(vals), 2),
                min=min(vals),
                max=max(vals),
            )
            for key, vals in sorted(groups.items())
        ]
    return SeriesOut(metric=metric, unit=UNITS[metric], bucket=bucket, start=start, end=end, points=points)


@router.get("/dashboard", response_model=Dashboard)
def dashboard(
    user: CurrentUser, db: DbSession, days: Annotated[int, Query(ge=7, le=MAX_RANGE_DAYS)] = 60, end: EndD = None
):
    """Everything for the charts screen in one call: profile, latest vitals and the last `days` days up to `end`
    (default today, UTC) of daily summaries, blood pressure, cycle and ECG list (no waveform), plus trend analysis."""
    start_d, end_d = _date_range(None, end, default_days=days)
    start = datetime.combine(start_d, time.min, UTC)
    stop = datetime.combine(end_d + timedelta(days=1), time.min, UTC)

    latest = {}
    for metric in UNITS:
        row = db.execute(
            select(VitalSample.ts, VitalSample.value)
            .where(VitalSample.user_id == user.id, VitalSample.metric == metric)
            .order_by(VitalSample.ts.desc())
            .limit(1)
        ).first()
        latest[metric] = LatestValue(ts=_utc(row.ts), value=row.value) if row else None

    age = None
    if user.birth_date:
        today, born = datetime.now(UTC).date(), user.birth_date
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    bmi = round(user.weight_kg / (user.height_cm / 100) ** 2, 1) if user.weight_kg and user.height_cm else None

    ecg = db.execute(
        select(
            EcgRecording.id,
            EcgRecording.started_at,
            EcgRecording.sample_rate_hz,
            EcgRecording.avg_heart_rate,
            EcgRecording.classification,
        )
        .where(EcgRecording.user_id == user.id, EcgRecording.started_at >= start, EcgRecording.started_at < stop)
        .order_by(EcgRecording.started_at.desc())
    ).all()

    return Dashboard(
        user_id=user.id,
        name=user.name,
        sex=user.sex,
        age=age,
        weight_kg=user.weight_kg,
        height_cm=user.height_cm,
        bmi=bmi,
        latest=latest,
        daily=db.scalars(
            select(DailySummary)
            .where(DailySummary.user_id == user.id, DailySummary.date.between(start_d, end_d))
            .order_by(DailySummary.date)
        ).all(),
        blood_pressure=db.scalars(
            select(BloodPressureReading)
            .where(
                BloodPressureReading.user_id == user.id,
                BloodPressureReading.ts >= start,
                BloodPressureReading.ts < stop,
            )
            .order_by(BloodPressureReading.ts)
        ).all(),
        cycle=db.scalars(
            select(CycleDay)
            .where(CycleDay.user_id == user.id, CycleDay.date.between(start_d, end_d))
            .order_by(CycleDay.date)
        ).all(),
        ecg=[EcgSummary.model_validate(r._asdict()) for r in ecg],
        stats=analyze(db, user.id, end=end, days=days, include_series=True),
    )

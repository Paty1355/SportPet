"""Odczyt danych zdrowotnych pod wykresy. Zawsze dane zalogowanego użytkownika (JWT)."""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models import BloodPressureReading, CycleDay, DailySummary, EcgRecording, VitalSample
from app.schemas.health import (
    BloodPressureOut,
    CycleOut,
    DailyOut,
    EcgDetail,
    EcgSummary,
    LatestValue,
    Overview,
    SeriesOut,
    SeriesPoint,
)

router = APIRouter(prefix="/health", tags=["health-charts"])

UNITS = {"heart_rate": "bpm", "spo2": "%", "stress": "score 0-100"}
BUCKET_SECONDS = {"raw": 0, "5m": 300, "15m": 900, "1h": 3600, "1d": 86400}
MAX_RANGE_DAYS = 60
MAX_RAW_RANGE_DAYS = 3  # raw to ~864 punktów/dobę/metrykę; dłuższe zakresy mają iść przez bucket


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


StartDT = Annotated[datetime | None, Query(description="ISO 8601 (ze strefą). Domyślnie end − 24 h")]
EndDT = Annotated[datetime | None, Query(description="ISO 8601 (ze strefą). Domyślnie teraz")]
StartD = Annotated[date | None, Query(description="YYYY-MM-DD, włącznie. Domyślnie 14 dni wstecz od end")]
EndD = Annotated[date | None, Query(description="YYYY-MM-DD, włącznie. Domyślnie dziś (UTC)")]


@router.get("/series", response_model=SeriesOut)
def series(
    user: CurrentUser,
    db: DbSession,
    metric: Literal["heart_rate", "spo2", "stress"],
    start: StartDT = None,
    end: EndDT = None,
    bucket: Literal["raw", "5m", "15m", "1h", "1d"] = "raw",
):
    """Szereg czasowy. bucket != raw zwraca średnią (`value`) oraz `min`/`max` w przedziale (UTC)."""
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


@router.get("/daily", response_model=list[DailyOut])
def daily(user: CurrentUser, db: DbSession, start: StartD = None, end: EndD = None):
    """Kroki i sen, jeden wiersz na dzień (rosnąco po dacie)."""
    start, end = _date_range(start, end, default_days=14)
    return db.scalars(
        select(DailySummary)
        .where(DailySummary.user_id == user.id, DailySummary.date.between(start, end))
        .order_by(DailySummary.date)
    ).all()


@router.get("/blood-pressure", response_model=list[BloodPressureOut])
def blood_pressure(user: CurrentUser, db: DbSession, start: StartDT = None, end: EndDT = None):
    start, end = _range(start, end, default_days=14)
    return db.scalars(
        select(BloodPressureReading)
        .where(BloodPressureReading.user_id == user.id, BloodPressureReading.ts >= start, BloodPressureReading.ts < end)
        .order_by(BloodPressureReading.ts)
    ).all()


@router.get("/cycle", response_model=list[CycleOut])
def cycle(user: CurrentUser, db: DbSession, start: StartD = None, end: EndD = None):
    """Pusta lista dla użytkowników bez danych cyklu (np. mężczyzn)."""
    start, end = _date_range(start, end, default_days=60)
    return db.scalars(
        select(CycleDay).where(CycleDay.user_id == user.id, CycleDay.date.between(start, end)).order_by(CycleDay.date)
    ).all()


@router.get("/ecg", response_model=list[EcgSummary])
def ecg_list(user: CurrentUser, db: DbSession, start: StartDT = None, end: EndDT = None):
    """Lista nagrań bez fali (fala jest duża: /ecg/{id})."""
    start, end = _range(start, end, default_days=14)
    rows = db.execute(
        select(
            EcgRecording.id,
            EcgRecording.started_at,
            EcgRecording.sample_rate_hz,
            EcgRecording.avg_heart_rate,
            EcgRecording.classification,
        )
        .where(EcgRecording.user_id == user.id, EcgRecording.started_at >= start, EcgRecording.started_at < end)
        .order_by(EcgRecording.started_at.desc())
    ).all()
    return [EcgSummary.model_validate(r._asdict()) for r in rows]


@router.get("/ecg/{ecg_id}", response_model=EcgDetail)
def ecg_detail(
    ecg_id: int,
    user: CurrentUser,
    db: DbSession,
    max_points: Annotated[int | None, Query(ge=100, le=20_000, description="zmniejsza falę co n-tą próbkę")] = None,
):
    rec = db.scalar(select(EcgRecording).where(EcgRecording.id == ecg_id, EcgRecording.user_id == user.id))
    if rec is None:
        raise HTTPException(404, "ECG recording not found")
    step = max(1, -(-len(rec.samples) // max_points)) if max_points else 1
    return EcgDetail(
        id=rec.id,
        started_at=rec.started_at,
        sample_rate_hz=rec.sample_rate_hz,
        avg_heart_rate=rec.avg_heart_rate,
        classification=rec.classification,
        samples=rec.samples[::step],
        returned_sample_rate_hz=rec.sample_rate_hz / step,
    )


@router.get("/overview", response_model=Overview)
def overview(user: CurrentUser, db: DbSession):
    """Najnowsze wartości do kafelków na dashboardzie."""
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
        today = datetime.now(UTC).date()
        born = user.birth_date
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    bmi = round(user.weight_kg / (user.height_cm / 100) ** 2, 1) if user.weight_kg and user.height_cm else None

    def newest(model, order_col):
        return db.scalars(select(model).where(model.user_id == user.id).order_by(order_col.desc()).limit(1)).first()

    return Overview(
        user_id=user.id,
        name=user.name,
        sex=user.sex,
        age=age,
        weight_kg=user.weight_kg,
        height_cm=user.height_cm,
        bmi=bmi,
        latest=latest,
        daily=newest(DailySummary, DailySummary.date),
        blood_pressure=newest(BloodPressureReading, BloodPressureReading.ts),
        cycle=newest(CycleDay, CycleDay.date),
    )

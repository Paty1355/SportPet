"""Health summary for the plan prompt: user profile plus medians of recent daily features."""

from datetime import UTC, date, datetime, timedelta
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CycleDay, PostWorkoutCheckIn, User
from app.schemas.plan import HealthSummary
from app.statistics.analyze import analyze
from app.statistics.daily import daily_features

WINDOW_DAYS = 14
DISTRESS_CODES = {"persistent_distress", "self_harm_risk"}
# user_id -> (day, overtraining signals): `analyze` covers 60 days, too slow to run on every chat message.
OVERTRAINING_CACHE: dict[int, tuple[date, list[str]]] = {}


def health_summary(db: Session, user: User) -> HealthSummary:
    end = datetime.now(UTC).date()
    start = end - timedelta(days=WINDOW_DAYS - 1)
    feats = daily_features(db, user.id, start, end)

    def values(metric: str) -> list[float]:
        return list(feats.get(metric, {}).values())

    def med(metric: str, digits: int | None = None) -> float | None:
        return round(median(vs), digits) if (vs := values(metric)) else None

    sleep = med("sleep_minutes")
    cycle = db.scalar(
        select(CycleDay)
        .where(CycleDay.user_id == user.id, CycleDay.date >= start)
        .order_by(CycleDay.date.desc())
        .limit(1)
    )
    birth = user.birth_date
    signals = overtraining_signals(db, user.id)

    return HealthSummary(
        sex=user.sex,
        age=end.year - birth.year - ((end.month, end.day) < (birth.month, birth.day)) if birth else None,
        bmi=round(user.weight_kg / (user.height_cm / 100) ** 2, 1) if user.weight_kg and user.height_cm else None,
        days_with_data=len({d for series in feats.values() for d in series}),
        resting_heart_rate=med("rhr"),
        sleep_hours=round(sleep / 60, 1) if sleep is not None else None,
        daily_steps=med("steps"),
        stress=med("stress_day_mean"),
        blood_pressure_systolic=med("bp_sys"),
        blood_pressure_diastolic=med("bp_dia"),
        spo2_min=min(values("spo2_min"), default=None),
        abnormal_ecg_days=int(sum(values("ecg_abnormal"))),
        cycle_phase=cycle.phase if cycle else None,
        cycle_day=cycle.cycle_day if cycle else None,
        cycle_length=cycle.cycle_length if cycle else None,
        overtraining=bool(signals),
        overtraining_signals=signals,
        mental_health_concern=bool(distress_codes(db, user.id)),
    )


def overtraining_signals(db: Session, user_id: int) -> list[str]:
    """Metrics behind the overtraining flag from `statistics.analyze`; empty when the flag is off."""
    result = analyze(db, user_id)["overtraining"]
    signals = [s["metric"] for s in result["signals"]] if result["flag"] else []
    OVERTRAINING_CACHE[user_id] = (datetime.now(UTC).date(), signals)
    return signals


def cached_overtraining_signals(db: Session, user_id: int) -> list[str]:
    """Same as `overtraining_signals`, computed at most once a day per user (plan generation refreshes it)."""
    cached = OVERTRAINING_CACHE.get(user_id)
    if cached is not None and cached[0] == datetime.now(UTC).date():
        return cached[1]
    return overtraining_signals(db, user_id)


def distress_codes(db: Session, user_id: int) -> set[str]:
    """Distress or self-harm codes reported in post-workout check-ins of the last `WINDOW_DAYS` days."""
    since = datetime.now(UTC) - timedelta(days=WINDOW_DAYS)
    rows = db.scalars(
        select(PostWorkoutCheckIn.safety_observations).where(
            PostWorkoutCheckIn.user_id == user_id, PostWorkoutCheckIn.workout_ended_at >= since
        )
    )
    return {item.get("code") for observations in rows for item in observations or []} & DISTRESS_CODES

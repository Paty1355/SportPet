
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from statistics import median
from zoneinfo import ZoneInfo

from app.schemas.post_workout import MetricComparison, Observation, PainStatistics, Period, ReportStatistics

MIN_COMPARISON_SAMPLES = 3
ANALYSIS_VERSION = "1"
METRICS = {
    "fatigueLevel": "fatigue_level",
    "moodLevel": "mood_level",
    "motivationLevel": "motivation_level",
    "perceivedExertionRating": "perceived_exertion_rating",
}


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def calendar_period(period: Period, anchor: date) -> tuple[date, date]:
    if period == "daily":
        return anchor, anchor
    if period == "weekly":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    start = anchor.replace(day=1)
    following = (
        start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
    )
    return start, following - timedelta(days=1)


def period_bounds(start: date, end: date, timezone: str) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone)
    return (
        datetime.combine(start, time.min, zone).astimezone(UTC),
        datetime.combine(end + timedelta(days=1), time.min, zone).astimezone(UTC),
    )


def compare_checkins(current: list, previous: list) -> ReportStatistics:
    metrics = {}
    for key, attribute in METRICS.items():
        values = [getattr(row, attribute) for row in current if getattr(row, attribute) is not None]
        previous_values = [getattr(row, attribute) for row in previous if getattr(row, attribute) is not None]
        enough = len(values) >= MIN_COMPARISON_SAMPLES and len(previous_values) >= MIN_COMPARISON_SAMPLES
        current_median = float(median(values)) if values else None
        previous_median = float(median(previous_values)) if previous_values else None
        metrics[key] = MetricComparison(
            count=len(values),
            median=current_median,
            previous_count=len(previous_values),
            previous_median=previous_median,
            delta=current_median - previous_median if enough else None,
            status="ok" if enough else "insufficient_data",
        )
    changes = Counter(row.feeling_change for row in current if row.feeling_change is not None)
    return ReportStatistics(
        sample_count=len(current),
        previous_sample_count=len(previous),
        status="ok" if any(item.status == "ok" for item in metrics.values()) else "insufficient_data",
        metrics=metrics,
        feeling_change={key: changes[key] for key in ("better", "same", "worse")},
        pain=PainStatistics(
            answered_count=sum(row.pain_experienced is not None for row in current),
            reported_count=sum(row.pain_experienced is True for row in current),
        ),
    )


def observations_for(statistics: ReportStatistics) -> list[Observation]:
    result = []
    names = {
        "fatigueLevel": "fatigue",
        "moodLevel": "mood",
        "motivationLevel": "motivation",
        "perceivedExertionRating": "workout effort",
    }
    for key, metric in statistics.metrics.items():
        if metric.status != "ok":
            continue
        direction = "higher" if metric.delta > 0 else "lower" if metric.delta < 0 else "unchanged"
        result.append(
            Observation(
                id=f"{key}:{direction}",
                text=(f"Your median reported {names[key]} was {direction} compared with the previous period."),
            )
        )
    if statistics.pain.reported_count:
        result.append(
            Observation(id="pain:reported", text="You reported pain in at least one check-in during this period.")
        )
    if statistics.status == "insufficient_data":
        result.append(
            Observation(
                id="comparison:insufficient_data",
                text=("There are not enough comparable check-ins to describe a change between periods yet."),
            )
        )
    return result

from datetime import date, timedelta
from types import SimpleNamespace

from app.statistics.post_workout import calendar_period, compare_checkins, period_bounds


def row(fatigue, mood=7, motivation=8, effort=6, feeling="better", pain=False):
    return SimpleNamespace(
        fatigue_level=fatigue,
        mood_level=mood,
        motivation_level=motivation,
        perceived_exertion_rating=effort,
        feeling_change=feeling,
        pain_experienced=pain,
    )


def test_comparisons_use_per_metric_counts_and_skip_missing():
    current = [row(0, motivation=None), row(2), row(4)]
    previous = [row(5), row(6), row(7)]
    result = compare_checkins(current, previous)
    assert result.metrics["fatigueLevel"].median == 2
    assert result.metrics["fatigueLevel"].delta == -4
    assert result.metrics["fatigueLevel"].status == "ok"
    assert result.metrics["motivationLevel"].count == 2
    assert result.metrics["motivationLevel"].status == "insufficient_data"
    assert result.metrics["motivationLevel"].delta is None


def test_empty_period_is_not_a_zero_score():
    result = compare_checkins([], [row(5)])
    assert result.sample_count == 0
    assert result.metrics["fatigueLevel"].median is None
    assert result.metrics["fatigueLevel"].delta is None
    assert result.status == "insufficient_data"


def test_pain_denominator_excludes_unknown_and_feelings_are_categories():
    result = compare_checkins(
        [row(3, pain=True), row(4, feeling="worse", pain=False), row(5, feeling=None, pain=None)], []
    )
    assert result.pain.answered_count == 2
    assert result.pain.reported_count == 1
    assert result.feeling_change == {"better": 1, "same": 0, "worse": 1}


def test_calendar_week_and_month_boundaries():
    assert calendar_period("weekly", date(2026, 10, 4)) == (date(2026, 9, 28), date(2026, 10, 4))
    assert calendar_period("monthly", date(2024, 2, 15)) == (date(2024, 2, 1), date(2024, 2, 29))
    assert calendar_period("monthly", date(2026, 12, 15)) == (date(2026, 12, 1), date(2026, 12, 31))


def test_local_day_handles_daylight_saving_time():
    start, end = period_bounds(date(2026, 3, 29), date(2026, 3, 29), "Europe/Warsaw")
    assert end - start == timedelta(hours=23)
    start, end = period_bounds(date(2026, 10, 25), date(2026, 10, 25), "Europe/Warsaw")
    assert end - start == timedelta(hours=25)

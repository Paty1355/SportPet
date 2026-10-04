from datetime import date

from app.agents.plan.agent import PLAN_DAYS, plan_dates

SUNDAY = date(2026, 10, 4)
WEDNESDAY = date(2026, 10, 7)


def test_weekdays_start_from_next_matching_day():
    assert plan_dates(PLAN_DAYS["mwf"], SUNDAY) == [date(2026, 10, 5), date(2026, 10, 7), date(2026, 10, 9)]


def test_today_counts_when_it_matches():
    assert plan_dates(PLAN_DAYS["mwf"], WEDNESDAY) == [date(2026, 10, 12), date(2026, 10, 7), date(2026, 10, 9)]
    assert plan_dates(PLAN_DAYS["weekends"], SUNDAY) == [date(2026, 10, 10), date(2026, 10, 4)]


def test_flexible_is_every_other_day_from_today():
    assert plan_dates(PLAN_DAYS["flexible"], SUNDAY) == [date(2026, 10, 4), date(2026, 10, 6), date(2026, 10, 8)]

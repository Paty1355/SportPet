from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models
from app.db.base import Base
from app.models import PostWorkoutCheckIn, User
from app.statistics import analyze
from app.statistics.charts import figures
from app.statistics.weekly import analyze_checkins

START, END = date(2026, 8, 3), date(2026, 9, 6)


def checkin(day: date, rpe: int, pain: bool) -> PostWorkoutCheckIn:
    return PostWorkoutCheckIn(
        user_id=1,
        request_id=f"{day}",
        start_payload_hash="x",
        workout_ended_at=datetime(day.year, day.month, day.day, 16, tzinfo=UTC),
        workout_duration_minutes=60,
        status="completed",
        perceived_exertion_rating=rpe,
        fatigue_level=rpe,
        mood_level=10 - rpe,
        motivation_level=6,
        feeling_change="better" if rpe < 8 else "worse",
        pain_experienced=pain,
        pain_intensity=4 if pain else 0,
        pain_locations=["Knee "] if pain else [],
    )


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        session.add(User(id=1, email="a@b.pl", hashed_password="x"))
        for week in range(4):
            monday = START + timedelta(weeks=week)
            session.add_all(checkin(monday + timedelta(days=d), 5, d == 4) for d in (0, 2, 4))
        session.add_all(checkin(START + timedelta(weeks=4, days=d), 8, False) for d in range(5))
        unfinished = checkin(START + timedelta(days=1), 10, False)
        unfinished.status = "in_progress"
        session.add(unfinished)
        session.commit()
        yield session


def test_weekly_statistics_and_load(db):
    res = analyze_checkins(db, 1, START, END, "Europe/Warsaw")
    weeks = res["weeks"]
    assert res["status"] == "ok" and res["checkin_count"] == 17 and len(weeks) == 5
    assert not any(w["partial"] for w in weeks)
    assert [w["workouts"] for w in weeks] == [3, 3, 3, 3, 5] and weeks[0]["load"] == 900 and weeks[4]["load"] == 2400
    assert weeks[0]["metrics"]["rpe"]["delta"] is None and weeks[1]["metrics"]["rpe"]["delta"] == 0
    assert weeks[4]["metrics"]["rpe"]["delta"] == 3 and weeks[4]["metrics"]["mood"]["median"] == 2
    assert weeks[0]["monotony"] == pytest.approx(0.80, abs=0.01)
    assert [w["acwr"] for w in weeks[:3]] == [None] * 3 and weeks[3]["acwr"] == pytest.approx(1.0)
    assert weeks[4]["acwr"] == pytest.approx(2400 / 1275) and res["acwr_high_weeks"] == ["2026-08-31"]
    assert weeks[0]["pain_share"] == pytest.approx(1 / 3) and res["pain_locations"] == {"knee": 4}
    assert weeks[4]["feeling_change"] == {"better": 0, "same": 0, "worse": 5}
    rpe_mood = next(c for c in res["correlations"] if (c["x"], c["y"]) == ("rpe", "mood"))
    assert rpe_mood["n"] == 17 and rpe_mood["rho"] < -0.9 and rpe_mood["p_adj"] < 0.05
    assert all(c["x"] not in ("stress", "sleep") for c in res["correlations"])


def test_report_pages_and_empty_user(db):
    import json

    result = analyze(db, 1, end=END, days=35, include_series=True)
    result["checkins"] = analyze_checkins(db, 1, START, END, "Europe/Warsaw")
    json.dumps(result)
    names = [n for n, _ in figures(result) if n.startswith("checkins")]
    assert names == ["checkins_weekly", "checkins_load", "checkins_correlations", "checkins_pain", "checkins_feeling"]
    empty = analyze_checkins(db, 2, START, END, "Europe/Warsaw")
    assert empty["status"] == "insufficient_data" and empty["acwr_high_weeks"] == []
    assert [n for n, _ in figures({**result, "checkins": empty}) if n.startswith("checkins")] == []

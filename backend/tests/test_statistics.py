from datetime import UTC, date, datetime, timedelta

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models import DailySummary, User, VitalSample
from app.statistics import analyze
from app.statistics.analyze import analyze_series
from app.statistics.charts import figures, render_pdf
from app.statistics.daily import weekly_sd

END = date(2026, 6, 30)


def series(values) -> dict:
    return {END - timedelta(days=len(values) - 1 - i): float(v) for i, v in enumerate(values)}


def test_detects_upward_trend_and_changepoint():
    rng = np.random.default_rng(0)
    r = analyze_series(series(60 + 0.3 * np.arange(56) + rng.normal(0, 1, 56)), END)
    assert r["trend"]["p"] < 0.001 and 1.5 < r["trend"]["slope_per_week"] < 2.7
    lo, hi = r["trend"]["ci95_per_week"]
    assert lo < r["trend"]["slope_per_week"] < hi


def test_step_change_date_and_recent_shift():
    rng = np.random.default_rng(1)
    r = analyze_series(series(np.r_[np.full(45, 58.0), np.full(11, 66.0)] + rng.normal(0, 1, 56)), END)
    assert r["change_point"]["date"] == (END - timedelta(days=10)).isoformat()
    assert r["baseline_vs_recent"]["delta"] > 6 and r["baseline_vs_recent"]["cliffs_delta"] > 0.8


def test_white_noise_rarely_significant():
    p = [analyze_series(series(np.random.default_rng(s).normal(60, 5, 56)), END)["trend"]["p"] for s in range(200)]
    hits = sum(x < 0.05 for x in p)
    assert hits <= 20  # 5% nominal; margin for randomness


def test_outlier_day_flagged_and_short_series_insufficient():
    vals = np.random.default_rng(2).normal(60, 2, 56)
    vals[-1] = 90
    assert [o["date"] for o in analyze_series(series(vals), END)["outlier_days"]] == [END.isoformat()]
    assert analyze_series(series(vals[:20]), END)["status"] == "insufficient_data"


def test_analyze_from_db_end_to_end():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        db.add(User(id=1, email="a@b.pl", hashed_password="x"))
        rng = np.random.default_rng(3)
        for i in range(40):
            day = END - timedelta(days=39 - i)
            db.add(DailySummary(user_id=1, date=day, steps=int(8000 + 100 * i + rng.normal(0, 300)), sleep_minutes=420))
            midnight = datetime(day.year, day.month, day.day, tzinfo=UTC)
            db.add_all(
                VitalSample(
                    user_id=1,
                    metric="heart_rate",
                    ts=midnight + timedelta(minutes=5 * m),
                    value=55 + 0.2 * i + rng.normal(0, 2),
                )  # noqa: E501
                for m in range(24 * 12)
            )
        db.commit()
        res = analyze(db, 1, end=END, days=40)
    assert res["metrics"]["steps"]["trend"]["p_adj"] < 0.001
    assert res["metrics"]["rhr"]["trend"]["slope_per_week"] > 0.8
    assert res["metrics"]["sleep_minutes"]["trend"]["p"] == 1.0  # constant 420
    assert res["metrics"]["bp_sys"]["status"] == "insufficient_data" and res["cycle"] == []


def test_weekly_sd_blocks_do_not_overlap_and_trend_fp_is_low():
    start = END - timedelta(days=59)
    bp = {start + timedelta(days=i): 120.0 + (i % 7) for i in range(60)}  # every week: SD 2.16
    w = weekly_sd(bp, start, END)
    assert len(w) == 8 and min(w) == END - timedelta(days=49) and {round(v, 2) for v in w.values()} == {2.16}
    fp = 0
    for s in range(300):
        r = np.random.default_rng(s)
        noisy = {start + timedelta(days=i): float(r.normal(120, 5)) for i in range(60)}
        res = analyze_series(weekly_sd(noisy, start, END), END, 8)
        fp += res["trend"]["p"] < 0.05
    assert fp <= 30


def test_include_series_and_pdf_render(tmp_path):
    import json
    from io import BytesIO

    from pypdf import PdfReader

    rng = np.random.default_rng(5)
    vals = 60 + 0.3 * np.arange(56) + rng.normal(0, 1, 56)
    vals[-1] += 15
    r = analyze_series(series(vals), END, with_series=True)
    assert len(r["series"]) == 56 and r["trend_line"][0]["date"] == r["series"][0]["date"]
    assert abs(r["trend_line"][1]["value"] - vals[-1]) < 20 and "series" not in analyze_series(series(vals), END)
    result = {
        "metrics": {
            "rhr": {
                **r,
                "trend": {**r["trend"], "p_adj": 0.0},
                "change_point": {**r["change_point"], "p_adj": 0.0},
                "baseline_vs_recent": {**r["baseline_vs_recent"], "p_adj": 0.01},
            },
            "steps": analyze_series(series(vals[:10]), END, with_series=True),
        },
        "lagged_correlations": [
            {"x": "sleep_minutes", "y": "rhr", "lag_days": 0, "n": 30, "rho": -0.4, "p": 0.01, "p_adj": 0.02}
        ],
        "cycle": [{"metric": "rhr", "p": 0.01, "p_adj": 0.02, "median_by_phase": {"luteal": 61.0, "follicular": 58.0}}],
    }
    json.dumps(result)
    assert [n for n, _ in figures(result)] == ["significance", "correlations", "cycle", "rhr", "steps"]
    buf = BytesIO()
    render_pdf(result, buf)
    assert len(PdfReader(BytesIO(buf.getvalue())).pages) == 5

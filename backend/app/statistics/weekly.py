
from collections import Counter, defaultdict
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import numpy as np
from matplotlib.figure import Figure
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PostWorkoutCheckIn
from app.statistics import trends
from app.statistics.analyze import _adjust
from app.statistics.charts import A4_WIDTH, ALPHA, C_BASE, C_RECENT, C_SERIES, C_TREND, _d, _style
from app.statistics.daily import Series, daily_features
from app.statistics.post_workout import MIN_COMPARISON_SAMPLES, period_bounds, utc

CHECKIN_METRICS = {
    "rpe": "perceived_exertion_rating",
    "mood": "mood_level",
    "fatigue": "fatigue_level",
    "motivation": "motivation_level",
    "pain": "pain_intensity",
}
WATCH_METRICS = {"stress": "stress_day_mean", "sleep": "sleep_minutes"}
LABELS = {
    "rpe": ("Perceived exertion (RPE)", "0-10"),
    "mood": ("Mood", "0-10"),
    "fatigue": ("Fatigue", "0-10"),
    "motivation": ("Motivation", "0-10"),
    "pain": ("Post-workout pain (DOMS proxy)", "0-10"),
    "stress": ("Daytime stress (watch)", "score 0-100"),
    "sleep": ("Sleep", "min"),
}
GRID = ("rpe", "mood", "stress", "pain")
CORRELATION_PAIRS = (
    ("rpe", "mood"), ("rpe", "fatigue"), ("pain", "motivation"), ("stress", "rpe"), ("stress", "mood"),
    ("sleep", "rpe"), ("sleep", "mood"),
)
ACWR_SAFE, ACWR_HIGH = (0.8, 1.3), 1.5
FEELINGS = ("better", "same", "worse")
TOP_LOCATIONS = 8


def _summary(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "median": None, "q1": None, "q3": None}
    q1, median, q3 = np.percentile(values, [25, 50, 75])
    return {"n": len(values), "median": float(median), "q1": float(q1), "q3": float(q3)}


def _per_day(checkins: list[tuple[date, PostWorkoutCheckIn]], attribute: str) -> Series:
    by_day = defaultdict(list)
    for day, row in checkins:
        if (value := getattr(row, attribute)) is not None:
            by_day[day].append(value)
    return {day: float(np.mean(values)) for day, values in by_day.items()}


def load_indices(daily_load: Series, start: date, anchor: date) -> dict:

    def last(days: int) -> list[float]:
        return [daily_load.get(anchor - timedelta(days=i), 0.0) for i in range(days)]

    out = {"monotony": None, "strain": None, "acwr": None}
    if anchor - timedelta(days=6) >= start:
        week = last(7)
        if (sd := float(np.std(week, ddof=1))) > 0:
            out["monotony"] = float(np.mean(week)) / sd
            out["strain"] = sum(week) * out["monotony"]
    if anchor - timedelta(days=27) >= start and (chronic := sum(last(28)) / 4) > 0:
        out["acwr"] = sum(last(7)) / chronic
    return out


def analyze_checkins(db: Session, user_id: int, start: date, end: date, timezone: str) -> dict:
    lo, hi = period_bounds(start, end, timezone)
    zone = ZoneInfo(timezone)
    rows = db.scalars(
        select(PostWorkoutCheckIn)
        .where(
            PostWorkoutCheckIn.user_id == user_id,
            PostWorkoutCheckIn.status == "completed",
            PostWorkoutCheckIn.workout_ended_at >= lo,
            PostWorkoutCheckIn.workout_ended_at < hi,
        )
        .order_by(PostWorkoutCheckIn.workout_ended_at)
    ).all()
    checkins = [(utc(row.workout_ended_at).astimezone(zone).date(), row) for row in rows]
    feats = daily_features(db, user_id, start, end)
    daily = {key: _per_day(checkins, attribute) for key, attribute in CHECKIN_METRICS.items()}
    daily |= {key: feats.get(feature, {}) for key, feature in WATCH_METRICS.items()}

    daily_load: Series = defaultdict(float)
    for day, row in checkins:
        if row.perceived_exertion_rating is not None and row.workout_duration_minutes:
            daily_load[day] += row.perceived_exertion_rating * row.workout_duration_minutes

    weeks, previous = [], None
    monday = start - timedelta(days=start.weekday())
    while monday <= end:
        sunday = monday + timedelta(days=6)
        week_rows = [row for day, row in checkins if monday <= day <= sunday]
        metrics = {
            key: _summary([float(v) for row in week_rows if (v := getattr(row, attribute)) is not None])
            for key, attribute in CHECKIN_METRICS.items()
        }
        metrics |= {
            key: _summary([v for day, v in daily[key].items() if monday <= day <= sunday]) for key in WATCH_METRICS
        }
        for key, metric in metrics.items():
            before = previous["metrics"][key] if previous else None
            enough = before and metric["n"] >= MIN_COMPARISON_SAMPLES and before["n"] >= MIN_COMPARISON_SAMPLES
            metric["delta"] = metric["median"] - before["median"] if enough else None
        pain = [row.pain_experienced for row in week_rows if row.pain_experienced is not None]
        feelings = Counter(row.feeling_change for row in week_rows if row.feeling_change)
        previous = {
            "start": monday.isoformat(),
            "end": sunday.isoformat(),
            "partial": monday < start or sunday > end,
            "workouts": len(week_rows),
            "minutes": sum(row.workout_duration_minutes or 0 for row in week_rows),
            "load": sum(v for day, v in daily_load.items() if monday <= day <= sunday),
            **load_indices(daily_load, start, min(sunday, end)),
            "pain_share": sum(pain) / len(pain) if pain else None,
            "feeling_change": {key: feelings[key] for key in FEELINGS},
            "metrics": metrics,
        }
        weeks.append(previous)
        monday += timedelta(days=7)

    correlations = []
    for x, y in CORRELATION_PAIRS:
        if res := trends.lagged_spearman(daily[x], daily[y], 0):
            correlations.append({"x": x, "y": y, "n": res[0], "rho": res[1], "p": res[2]})
    _adjust(correlations)

    locations = Counter(loc.strip().lower() for _, row in checkins for loc in row.pain_locations or [] if loc.strip())
    return {
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "status": "ok" if len(checkins) >= MIN_COMPARISON_SAMPLES else "insufficient_data",
        "checkin_count": len(checkins),
        "weeks": weeks,
        "pain_locations": dict(locations.most_common(TOP_LOCATIONS)),
        "correlations": correlations,
        "acwr_high_weeks": [w["start"] for w in weeks if w["acwr"] is not None and w["acwr"] > ACWR_HIGH],
    }


def _x(weeks: list[dict]) -> tuple[np.ndarray, list[str]]:
    return np.arange(len(weeks)), [f"{_d(w['start']):%d.%m}{'*' if w['partial'] else ''}" for w in weeks]


def _col(values) -> np.ndarray:
    return np.array([np.nan if v is None else v for v in values], dtype=float)


def _title(fig: Figure, text: str) -> None:
    fig.suptitle(text, x=0.01, ha="left", fontsize=11, fontweight="bold")


def plot_weekly_metrics(result: dict) -> Figure | None:
    if result["status"] != "ok":
        return None
    weeks = result["weeks"]
    x, labels = _x(weeks)
    fig = Figure(figsize=(A4_WIDTH, 6.0), layout="constrained")
    with _style():
        axes = fig.subplots(2, 2, sharex=True).ravel()
    for ax, key in zip(axes, GRID, strict=True):
        metrics = [w["metrics"][key] for w in weeks]
        q1, q3 = _col(m["q1"] for m in metrics), _col(m["q3"] for m in metrics)
        ax.fill_between(x, q1, q3, color=C_SERIES, alpha=0.15)
        ax.plot(x, _col(m["median"] for m in metrics), color=C_SERIES, marker="o", markersize=4)
        title, unit = LABELS[key]
        ax.set_title(f"{title} [{unit}]", fontsize=9)
        ax.set_xticks(x, labels, rotation=45, fontsize=7)
    _title(fig, "Weekly check-ins: median with IQR band (* = partial week)")
    return fig


def plot_training_load(result: dict) -> Figure | None:
    weeks = result["weeks"]
    if not any(w["load"] for w in weeks):
        return None
    x, labels = _x(weeks)
    fig = Figure(figsize=(A4_WIDTH, 3.8), layout="constrained")
    with _style():
        ax = fig.subplots()
    ax.bar(x, [w["load"] for w in weeks], color=C_BASE, label="weekly load (RPE x min)")
    ax.set_ylabel("RPE x min")
    ax.set_xticks(x, labels, rotation=45, fontsize=7)
    ax2 = ax.twinx()
    ax2.grid(False)
    ax2.axhspan(*ACWR_SAFE, color="#2f855a", alpha=0.12, lw=0, label=f"ACWR {ACWR_SAFE[0]}-{ACWR_SAFE[1]}")
    ax2.axhline(ACWR_HIGH, color=C_TREND, ls="--", lw=1, label=f"ACWR {ACWR_HIGH}")
    ax2.plot(x, _col(w["acwr"] for w in weeks), color=C_RECENT, marker="o", label="ACWR (7 d / 28 d)")
    ax2.set_ylabel("ACWR")
    last = next((w for w in reversed(weeks) if w["monotony"] is not None), None)
    if last:
        ax.set_title(
            f"week {_d(last['start']):%d.%m}: monotony {last['monotony']:.2f}, strain {last['strain']:.0f}",
            loc="left",
            fontsize=8,
            color="#4a5568",
        )
    handles, names = ax.get_legend_handles_labels()
    handles2, names2 = ax2.get_legend_handles_labels()
    fig.legend(handles + handles2, names + names2, loc="outside lower center", ncol=4, fontsize=7, frameon=False)
    _title(fig, "Training load (sRPE) and acute:chronic workload ratio")
    return fig


def plot_checkin_correlations(result: dict) -> Figure | None:
    corr = result["correlations"]
    if not corr:
        return None
    fig = Figure(figsize=(A4_WIDTH, 0.4 * len(corr) + 1.4), layout="constrained")
    with _style():
        ax = fig.subplots()
    names = [f"{LABELS[c['x']][0]} ↔ {LABELS[c['y']][0]} (n={c['n']})" for c in corr]
    ax.barh(names, [c["rho"] for c in corr], color=[C_SERIES if c["p_adj"] < ALPHA else C_BASE for c in corr])
    for i, c in enumerate(corr):
        ax.text(c["rho"], i, f" {c['rho']:+.2f} (p_adj={c['p_adj']:.3f}) ", va="center", fontsize=7,
                ha="left" if c["rho"] >= 0 else "right")
    ax.set_xlim(-1, 1)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Spearman rho (same day, daily means)")
    _title(fig, "Check-in correlations (blue = p_adj < 0.05)")
    return fig


def plot_pain(result: dict) -> Figure | None:
    weeks = result["weeks"]
    if all(w["pain_share"] is None for w in weeks):
        return None
    x, labels = _x(weeks)
    fig = Figure(figsize=(A4_WIDTH, 3.6), layout="constrained")
    with _style():
        ax, ax_loc = fig.subplots(1, 2, width_ratios=(3, 2))
    ax.bar(x, 100 * _col(w["pain_share"] for w in weeks), color=C_TREND)
    ax.set_ylim(0, 100)
    ax.set_ylabel("% of workouts with pain")
    ax.set_xticks(x, labels, rotation=45, fontsize=7)
    locations = result["pain_locations"]
    if locations:
        ax_loc.barh(list(locations)[::-1], list(locations.values())[::-1], color=C_RECENT)
        ax_loc.set_xlabel("reports")
    else:
        ax_loc.text(0.5, 0.5, "no pain reported", ha="center", va="center", transform=ax_loc.transAxes)
        ax_loc.set_axis_off()
    _title(fig, "Pain after workouts")
    return fig


def plot_feeling_change(result: dict) -> Figure | None:
    weeks = result["weeks"]
    if not any(sum(w["feeling_change"].values()) for w in weeks):
        return None
    x, labels = _x(weeks)
    fig = Figure(figsize=(A4_WIDTH, 3.4), layout="constrained")
    with _style():
        ax = fig.subplots()
    bottom = np.zeros(len(weeks))
    for key, color in zip(FEELINGS, ("#2f855a", C_BASE, C_TREND), strict=True):
        counts = np.array([w["feeling_change"][key] for w in weeks])
        ax.bar(x, counts, bottom=bottom, color=color, label=key)
        bottom += counts
    ax.set_ylabel("check-ins")
    ax.set_xticks(x, labels, rotation=45, fontsize=7)
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower center", ncol=3, fontsize=7, frameon=False)
    _title(fig, "Feeling compared with before the workout")
    return fig


def figures(result: dict) -> list[tuple[str, Figure]]:
    out = [
        ("checkins_weekly", plot_weekly_metrics(result)),
        ("checkins_load", plot_training_load(result)),
        ("checkins_correlations", plot_checkin_correlations(result)),
        ("checkins_pain", plot_pain(result)),
        ("checkins_feeling", plot_feeling_change(result)),
    ]
    return [(n, f) for n, f in out if f is not None]

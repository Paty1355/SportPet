"""User trend analysis: daily features -> tests -> JSON-serializable result (for the report / AI model context)."""

from datetime import UTC, date, datetime, timedelta

import numpy as np
from scipy import stats
from sqlalchemy.orm import Session

from app.statistics import trends
from app.statistics.daily import Series, cycle_phases, daily_features

DEFAULT_DAYS = 60
MIN_DAYS = 28  # with fewer days of data we draw no trend conclusion: "insufficient_data", not "no trend"
RECENT_DAYS = 7
BASELINE_DAYS = 28  # days immediately before the "recent" window
MIN_BASELINE, MIN_RECENT = 14, 4
MIN_POINTS = {"bp_sys_sd_wk": 8}  # 1 point per week (60 days = 8 full blocks): different minimum than daily
OUTLIER_Z = 2.0
METRICS = (
    "rhr", "night_dip", "stress_day_mean", "stress_high_frac", "spo2_min", "spo2_low_count", "bp_sys", "bp_dia",
    "bp_am_pm_diff", "bp_sys_sd_wk", "steps", "sleep_minutes", "ecg_hr", "ecg_abnormal",
)  # fmt: skip
# (cause D, effect D+lag); lag 0..2 days
LAG_PAIRS = (("sleep_minutes", "rhr"), ("sleep_minutes", "stress_day_mean"), ("steps", "rhr"))
LAGS = (0, 1, 2)
CYCLE_METRICS = ("rhr", "stress_day_mean")
# Overtraining: (bad direction, min recent-vs-baseline change, min slope per week).
# ponytail: heuristic thresholds (rhr from the README, the rest hand-picked); HRV unavailable, so not used.
OVERTRAINING = {
    "rhr": (1, 5.0, 1.0),
    "night_dip": (-1, 3.0, 1.0),
    "stress_day_mean": (1, 5.0, 2.0),
    "sleep_minutes": (-1, 30.0, 15.0),
}
OVERTRAINING_MIN_SIGNALS = 2  # rhr is mandatory
ALPHA = 0.05


def analyze_series(s: Series, end: date, min_n: int = MIN_DAYS, with_series: bool = False) -> dict:
    """Tests of a single metric. `end` = last day of the analysis (the "recent" window is `end` - 6 .. `end`).

    Returns {"status": "insufficient_data", "n", "required"} or {"status": "ok", "n", "trend", "change_point",
    "baseline_vs_recent", "outlier_days"}. "p" fields are raw; "p_adj" is added by `analyze` (Benjamini-Hochberg).
    `with_series=True` adds "series" ([{date, value}] ascending; also for insufficient_data) and "trend_line"
    (Sen line: points on the first and last day, for charts)."""
    pts = sorted(s.items())
    n = len(pts)
    series = [{"date": d.isoformat(), "value": v} for d, v in pts] if with_series else None
    if n < min_n:
        return {"status": "insufficient_data", "n": n, "required": min_n, **({"series": series} if with_series else {})}

    dates = [d for d, _ in pts]
    y = np.array([v for _, v in pts])
    x = np.array([(d - dates[0]).days for d in dates], dtype=float)

    slope, lo, hi = trends.sen_slope(x, y)
    cp_idx, cp_p = trends.pettitt(y)
    out = {
        "status": "ok",
        "n": n,
        "trend": {"slope_per_week": slope * 7, "ci95_per_week": [lo * 7, hi * 7], "p": trends.mann_kendall(x, y)},
        "change_point": {
            "date": dates[cp_idx].isoformat(),
            "before_median": float(np.median(y[:cp_idx])),
            "after_median": float(np.median(y[cp_idx:])),
            "p": cp_p,
        },
        "baseline_vs_recent": None,
        "outlier_days": [],
    }
    if with_series:
        intercept = float(np.median(y) - slope * np.median(x))  # intercept Theila-Sena
        out["series"] = series
        out["trend_line"] = [{"date": dates[i].isoformat(), "value": intercept + slope * x[i]} for i in (0, n - 1)]

    recent_start = end - timedelta(days=RECENT_DAYS - 1)
    baseline = np.array([v for d, v in pts if recent_start - timedelta(days=BASELINE_DAYS) <= d < recent_start])
    recent = {d: v for d, v in pts if d >= recent_start}
    if len(baseline) >= MIN_BASELINE and len(recent) >= MIN_RECENT:
        p, cliff = trends.compare(baseline, np.array(list(recent.values())))
        out["baseline_vs_recent"] = {
            "baseline_median": float(np.median(baseline)),
            "recent_median": float(np.median(list(recent.values()))),
            "delta": float(np.median(list(recent.values())) - np.median(baseline)),
            "cliffs_delta": cliff,
            "baseline_window": [
                (recent_start - timedelta(days=BASELINE_DAYS)).isoformat(),
                (recent_start - timedelta(days=1)).isoformat(),
            ],
            "recent_window": [recent_start.isoformat(), end.isoformat()],
            "p": p,
        }
        out["outlier_days"] = [
            {"date": d.isoformat(), "z": z} for d, z in trends.robust_z(baseline, recent).items() if abs(z) > OUTLIER_Z
        ]
    return out


def detect_overtraining(metrics: dict) -> dict:
    """Overtraining from a finished `analyze()["metrics"]` (after `p_adj` correction): a rise in RHR (required) together
    with at least one of: loss of the nocturnal heart-rate dip, higher stress, less sleep. A signal = a significant
    (`p_adj` < 0.05) change beyond the threshold in the bad direction.
    {"flag": bool, "signals": [{"metric", "delta", "slope_per_week"}]};
    `delta` = last 7 days minus baseline (or None)."""
    signals = []
    for name, (sign, min_delta, min_slope) in OVERTRAINING.items():
        r = metrics.get(name, {})
        if r.get("status") != "ok":
            continue
        bvr, tr = r["baseline_vs_recent"], r["trend"]
        by_delta = bvr and bvr["p_adj"] < ALPHA and sign * bvr["delta"] >= min_delta
        by_slope = tr["p_adj"] < ALPHA and sign * tr["slope_per_week"] >= min_slope
        if by_delta or by_slope:
            signals.append(
                {"metric": name, "delta": bvr["delta"] if bvr else None, "slope_per_week": tr["slope_per_week"]}
            )
    hit = {s["metric"] for s in signals}
    return {"flag": "rhr" in hit and len(hit) >= OVERTRAINING_MIN_SIGNALS, "signals": signals}


def _adjust(items: list[dict]) -> None:
    """Benjamini-Hochberg in place: adds "p_adj" to every dict that has "p"."""
    if items:
        for item, adj in zip(items, stats.false_discovery_control([i["p"] for i in items]), strict=True):
            item["p_adj"] = float(adj)


def analyze(
    db: Session, user_id: int, end: date | None = None, days: int = DEFAULT_DAYS, include_series: bool = False
) -> dict:
    """Full user analysis over `days` days up to and including `end` (default yesterday UTC: today is incomplete).

    {"window": {start, end}, "metrics": {nazwa: analyze_series}, "lagged_correlations": [...], "cycle": [...],
    "overtraining": {flag, signals}}.
    `include_series=True` adds a daily series and a trend line to every metric (for charts, see `charts.py`).
    P-values are corrected separately within each test family
    (trend, change point, baseline-vs-recent, correlations, cycle)."""
    end = end or datetime.now(UTC).date() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    feats = daily_features(db, user_id, start, end)

    metrics = {m: analyze_series(feats.get(m, {}), end, MIN_POINTS.get(m, MIN_DAYS), include_series) for m in METRICS}
    ok = [r for r in metrics.values() if r["status"] == "ok"]
    _adjust([r["trend"] for r in ok])
    _adjust([r["change_point"] for r in ok])
    _adjust([r["baseline_vs_recent"] for r in ok if r["baseline_vs_recent"]])

    corr = []
    for a, b in LAG_PAIRS:
        for lag in LAGS:
            res = trends.lagged_spearman(feats.get(a, {}), feats.get(b, {}), lag)
            if res:
                corr.append({"x": a, "y": b, "lag_days": lag, "n": res[0], "rho": res[1], "p": res[2]})
    _adjust(corr)

    cycle = []
    phases = cycle_phases(db, user_id, start, end)
    for m in CYCLE_METRICS if phases else ():
        res = trends.kruskal_by_group(feats.get(m, {}), phases)
        if res:
            cycle.append({"metric": m, "p": res[0], "median_by_phase": res[1]})
    _adjust(cycle)

    return {
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "metrics": metrics,
        "lagged_correlations": corr,
        "cycle": cycle,
        "overtraining": detect_overtraining(metrics),
    }

"""Analiza trendów użytkownika: cechy dzienne -> testy -> wynik JSON-owalny (do raportu / kontekstu modelu AI)."""

from datetime import UTC, date, datetime, timedelta

import numpy as np
from scipy import stats
from sqlalchemy.orm import Session

from app.statistics import trends
from app.statistics.daily import Series, cycle_phases, daily_features

DEFAULT_DAYS = 60
MIN_DAYS = 28  # poniżej tylu dób z danymi nie wnioskujemy o trendzie: "insufficient_data", nie "brak trendu"
RECENT_DAYS = 7
BASELINE_DAYS = 28  # doby bezpośrednio przed oknem "ostatnie"
MIN_BASELINE, MIN_RECENT = 14, 4
MIN_POINTS = {"bp_sys_sd_wk": 8}  # 1 punkt na tydzień (60 dób = 8 pełnych bloków), więc inne minimum niż dobowe
OUTLIER_Z = 2.0
METRICS = (
    "rhr", "night_dip", "stress_day_mean", "stress_high_frac", "spo2_min", "spo2_low_count", "bp_sys", "bp_dia",
    "bp_am_pm_diff", "bp_sys_sd_wk", "steps", "sleep_minutes", "ecg_hr", "ecg_abnormal",
)  # fmt: skip
# (przyczyna D, skutek D+lag); lag 0..2 dób
LAG_PAIRS = (("sleep_minutes", "rhr"), ("sleep_minutes", "stress_day_mean"), ("steps", "rhr"))
LAGS = (0, 1, 2)
CYCLE_METRICS = ("rhr", "stress_day_mean")


def analyze_series(s: Series, end: date, min_n: int = MIN_DAYS, with_series: bool = False) -> dict:
    """Testy jednej metryki. `end` = ostatnia doba analizy (okno "ostatnie" to `end` - 6 .. `end`).

    Zwraca {"status": "insufficient_data", "n", "required"} albo {"status": "ok", "n", "trend", "change_point",
    "baseline_vs_recent", "outlier_days"}. Pola "p" są surowe; "p_adj" dopisuje `analyze` (Benjamini-Hochberg).
    `with_series=True` dokłada "series" ([{date, value}] rosnąco; także przy insufficient_data) oraz "trend_line"
    (prosta Sena: punkty na pierwszej i ostatniej dobie, do wykresu)."""
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


def _adjust(items: list[dict]) -> None:
    """Benjamini-Hochberg in place: dopisuje "p_adj" do każdego słownika z "p"."""
    if items:
        for item, adj in zip(items, stats.false_discovery_control([i["p"] for i in items]), strict=True):
            item["p_adj"] = float(adj)


def analyze(
    db: Session, user_id: int, end: date | None = None, days: int = DEFAULT_DAYS, include_series: bool = False
) -> dict:
    """Pełna analiza użytkownika za `days` dób do `end` włącznie (domyślnie wczoraj UTC: dzisiejsza doba jest niepełna).

    {"window": {start, end}, "metrics": {nazwa: analyze_series}, "lagged_correlations": [...], "cycle": [...]}.
    `include_series=True` dokłada do każdej metryki szereg dzienny i prostą trendu (pod wykresy, patrz `charts.py`).
    P-value są korygowane osobno w każdej rodzinie testów (trend, przełom, bazowa-vs-ostatnie, korelacje, cykl)."""
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
    }

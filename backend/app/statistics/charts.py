
from datetime import date
from io import BytesIO
from pathlib import Path

import matplotlib.dates as mdates
import numpy as np
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

LABELS = {
    "rhr": ("Resting heart rate", "bpm"),
    "night_dip": ("Nocturnal heart rate dip", "bpm"),
    "stress_day_mean": ("Daytime stress", "score 0-100"),
    "stress_high_frac": ("Time share with high stress (>60)", "fraction"),
    "spo2_min": ("SpO₂, daily minimum", "%"),
    "spo2_low_count": ("SpO₂ <94%, sample count", "count"),
    "bp_sys": ("Systolic blood pressure (daily mean)", "mmHg"),
    "bp_dia": ("Diastolic blood pressure (daily mean)", "mmHg"),
    "bp_am_pm_diff": ("Systolic blood pressure: morning minus evening", "mmHg"),
    "bp_sys_sd_wk": ("Systolic blood pressure variability (SD, weekly)", "mmHg"),
    "steps": ("Steps", "steps"),
    "sleep_minutes": ("Sleep", "min"),
    "ecg_hr": ("ECG heart rate", "bpm"),
    "ecg_abnormal": ("ECG: non-sinus rhythm", "0/1"),
}
REFERENCE = {
    "spo2_min": (94, "threshold 94%"),
    "bp_sys": (135, "home threshold 135"),
    "bp_dia": (85, "home threshold 85"),
    "sleep_minutes": (360, "6 h"),
}
PHASES = ("menstrual", "follicular", "ovulation", "luteal")
ALPHA = 0.05
A4_WIDTH = 8.27
C_SERIES, C_TREND, C_BASE, C_RECENT, C_BREAK, C_OUT = "#2b6cb0", "#c53030", "#a0aec0", "#ed8936", "#6b46c1", "#e53e3e"


def _d(s: str) -> date:
    return date.fromisoformat(s)


def _style():
    return sns.axes_style("whitegrid")


def plot_metric(name: str, r: dict) -> Figure:
    title, unit = LABELS.get(name, (name, ""))
    fig = Figure(figsize=(A4_WIDTH, 3.8), layout="constrained")
    with _style():
        ax = fig.subplots()
    series = r.get("series") or []
    fig.suptitle(f"{title} [{unit}]", x=0.01, ha="left", fontsize=11, fontweight="bold")
    if not series:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", transform=ax.transAxes)
        return fig

    xs, ys = [_d(p["date"]) for p in series], [p["value"] for p in series]
    sns.lineplot(x=xs, y=ys, ax=ax, color=C_SERIES, marker="o", markersize=3, linewidth=1, label="daily value")

    if r["status"] != "ok":
        ax.text(
            0.5,
            0.92,
            f"not enough data for tests (n={r['n']}, required {r['required']})",
            ha="center",
            transform=ax.transAxes,
            color="#718096",
        )
    else:
        trend, cp, bvr = r["trend"], r["change_point"], r["baseline_vs_recent"]
        if bvr:
            delta = f" (Δ{bvr['delta']:+.1f}, p_adj={bvr['p_adj']:.3f})"
            for (lo, hi), color, label, med, extra in (
                (bvr["baseline_window"], C_BASE, "baseline", bvr["baseline_median"], ""),
                (bvr["recent_window"], C_RECENT, "last 7 days", bvr["recent_median"], delta),
            ):
                ax.axvspan(_d(lo), _d(hi), color=color, alpha=0.18, lw=0)
                ax.hlines(med, _d(lo), _d(hi), color=color, lw=2, label=f"{label}: median {med:.1f}{extra}")
        significant = trend["p_adj"] < ALPHA
        line = r["trend_line"]
        ax.plot(
            [_d(p["date"]) for p in line],
            [p["value"] for p in line],
            color=C_TREND if significant else "#718096",
            ls="-" if significant else "--",
            lw=1.8,
            label="trend (Sen)",
        )
        if cp["p_adj"] < ALPHA:
            x_cp = _d(cp["date"])
            ax.axvline(x_cp, color=C_BREAK, ls=":", lw=1.5, label=f"change {x_cp:%d.%m} (p_adj={cp['p_adj']:.3f})")
            ax.hlines(cp["before_median"], xs[0], x_cp, color=C_BREAK, lw=1.2)
            ax.hlines(cp["after_median"], x_cp, xs[-1], color=C_BREAK, lw=1.2)
        if r["outlier_days"]:
            by_date = dict(zip(xs, ys, strict=True))
            out = [(_d(o["date"]), by_date[_d(o["date"])]) for o in r["outlier_days"]]
            ax.scatter(*zip(*out, strict=True), color=C_OUT, s=40, zorder=5, label="outlier |z|>2")
        lo, hi = trend["ci95_per_week"]
        verdict = "significant" if significant else "no significant trend"
        ax.set_title(
            f"trend {trend['slope_per_week']:+.2f}/week [95% CI {lo:+.2f}; {hi:+.2f}], "
            f"p_adj={trend['p_adj']:.3f} ({verdict})",
            loc="left",
            fontsize=8,
            color="#4a5568",
        )

    if name in REFERENCE:
        value, label = REFERENCE[name]
        ax.axhline(value, color="#2f855a", ls="-.", lw=1, label=label)
    ax.set_ylabel(unit)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    if ax.get_legend():
        ax.get_legend().remove()
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower center", ncol=3, fontsize=7, frameon=False)
    return fig


def plot_significance(result: dict) -> Figure | None:
    rows = sorted(
        ((LABELS.get(m, (m,))[0], r["trend"]["p_adj"]) for m, r in result["metrics"].items() if r["status"] == "ok"),
        key=lambda t: t[1],
        reverse=True,
    )
    if not rows:
        return None
    fig = Figure(figsize=(A4_WIDTH, 0.35 * len(rows) + 1.2), layout="constrained")
    with _style():
        ax = fig.subplots()
    score = [-np.log10(max(p, 1e-12)) for _, p in rows]
    ax.barh([n for n, _ in rows], score, color=[C_TREND if p < ALPHA else C_BASE for _, p in rows])
    ax.axvline(-np.log10(ALPHA), color="black", ls="--", lw=1)
    ax.text(-np.log10(ALPHA) + 0.1, 0.01, "p_adj = 0.05", transform=ax.get_xaxis_transform(), fontsize=8)
    ax.set_xlabel("-log10(p_adj) of the trend test (further from the axis = stronger evidence)")
    fig.suptitle(
        "Trend significance (after Benjamini-Hochberg correction)", x=0.01, ha="left", fontsize=11, fontweight="bold"
    )
    return fig


def plot_correlations(result: dict) -> Figure | None:
    corr = result["lagged_correlations"]
    if not corr:
        return None
    pairs = list(dict.fromkeys((c["x"], c["y"]) for c in corr))
    lags = sorted({c["lag_days"] for c in corr})
    rho = np.full((len(pairs), len(lags)), np.nan)
    text = np.full(rho.shape, "", dtype=object)
    for c in corr:
        i, j = pairs.index((c["x"], c["y"])), lags.index(c["lag_days"])
        rho[i, j] = c["rho"]
        text[i, j] = f"{c['rho']:+.2f}{'*' if c['p_adj'] < ALPHA else ''}\n(n={c['n']})"
    fig = Figure(figsize=(A4_WIDTH, 0.7 * len(pairs) + 1.6), layout="constrained")
    with _style():
        ax = fig.subplots()
    names = [f"{LABELS[x][0]} → {LABELS[y][0]}" for x, y in pairs]
    sns.heatmap(
        rho,
        ax=ax,
        annot=text,
        fmt="",
        cmap="RdBu_r",
        vmin=-1,
        vmax=1,
        cbar_kws={"label": "Spearman rho"},
        xticklabels=[f"+{lag} d" for lag in lags],
        yticklabels=names,
        linewidths=1,
    )
    fig.suptitle("Lagged correlations (* p_adj < 0.05)", x=0.01, ha="left", fontsize=11, fontweight="bold")
    return fig


def plot_cycle(result: dict) -> Figure | None:
    cycle = result["cycle"]
    if not cycle:
        return None
    fig = Figure(figsize=(A4_WIDTH, 3.0), layout="constrained")
    with _style():
        axes = fig.subplots(1, len(cycle), squeeze=False)[0]
    for ax, c in zip(axes, cycle, strict=True):
        phases = [p for p in PHASES if p in c["median_by_phase"]]
        sns.pointplot(
            x=phases,
            y=[c["median_by_phase"][p] for p in phases],
            ax=ax,
            color=C_SERIES if c["p_adj"] < ALPHA else "#718096",
            linestyle="none",
            markersize=9,
        )
        title, unit = LABELS[c["metric"]]
        ax.set_title(f"{title} [{unit}]\np_adj={c['p_adj']:.3f}", fontsize=9)
        ax.set_ylabel("median")
    fig.suptitle("Effect of cycle phase (blue = significant)", x=0.01, ha="left", fontsize=11, fontweight="bold")
    return fig


def figures(result: dict) -> list[tuple[str, Figure]]:
    out = [
        ("significance", plot_significance(result)),
        ("correlations", plot_correlations(result)),
        ("cycle", plot_cycle(result)),
    ]
    out += [(m, plot_metric(m, r)) for m, r in result["metrics"].items()]
    if "checkins" in result:
        from app.statistics import weekly

        out += weekly.figures(result["checkins"])
    return [(n, f) for n, f in out if f is not None]


def render_pdf(result: dict, dest: str | Path | BytesIO) -> None:
    with PdfPages(dest) as pdf:
        for _, fig in figures(result):
            pdf.savefig(fig)


def to_png(fig: Figure, dpi: int = 150) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    return buf.getvalue()

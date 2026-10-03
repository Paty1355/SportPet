"""Statistical tests on daily series. Pure functions (numpy/scipy), no database access."""

from datetime import date, timedelta

import numpy as np
from scipy import stats

from app.statistics.daily import Series


def sen_slope(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Sen slope (median of pairwise slopes) and its 95% CI, in units of y per unit of x."""
    slope, _, lo, hi = stats.theilslopes(y, x, alpha=0.95)
    return float(slope), float(lo), float(hi)


def mann_kendall(x: np.ndarray, y: np.ndarray) -> float:
    """Two-sided Mann-Kendall p-value for a monotonic trend y(x), with autocorrelation correction (Hamed-Rao).

    The variance of S is multiplied by n/n*: computed from the significant rank autocorrelations
    of the series after removing the Sen trend.
    The factor never drops below 1, so the correction can only weaken significance, never add to it.
    Gaps between points are ignored (autocorrelation is computed over indices)."""
    n = len(y)
    s = float(np.sign(y[None, :] - y[:, None])[np.triu_indices(n, 1)].sum())
    _, ties = np.unique(y, return_counts=True)
    var = (n * (n - 1) * (2 * n + 5) - float((ties * (ties - 1) * (2 * ties + 5)).sum())) / 18

    slope = sen_slope(x, y)[0]
    r = stats.rankdata(y - slope * x)
    r = r - r.mean()
    denom = float((r * r).sum())
    factor = 1.0
    if denom > 0:
        k = np.arange(1, n - 1)
        rho = np.array([(r[:-i] * r[i:]).sum() / denom for i in k])
        bound = 1.96 * np.sqrt(n - k - 1)
        significant = (rho < (-1 - bound) / (n - k)) | (rho > (-1 + bound) / (n - k))
        w = (n - k) * (n - k - 1) * (n - k - 2) * rho
        factor = max(1.0, 1 + 2 / (n * (n - 1) * (n - 2)) * float(w[significant].sum()))

    if s == 0 or var <= 0:
        return 1.0
    z = (s - np.sign(s)) / np.sqrt(var * factor)
    return float(2 * stats.norm.sf(abs(z)))


def pettitt(y: np.ndarray) -> tuple[int, float]:
    """Pettitt test for a single change point. Returns (index of first point of the new regime, approx. p-value)."""
    n = len(y)
    t = np.arange(1, n)  # po t punktach
    u = 2 * np.cumsum(stats.rankdata(y))[:-1] - t * (n + 1)
    i = int(np.argmax(np.abs(u)))
    k = abs(float(u[i]))
    return i + 1, float(min(1.0, 2 * np.exp(-6 * k**2 / (n**3 + n**2))))


def compare(baseline: np.ndarray, recent: np.ndarray) -> tuple[float, float]:
    """Mann-Whitney U: (p-value, Cliff's delta). Delta is in [-1, 1]; positive = recent days higher than baseline."""
    u, p = stats.mannwhitneyu(recent, baseline, alternative="two-sided")
    p = 1.0 if np.isnan(p) else float(p)  # nan when all values are equal
    return p, float(2 * u / (len(recent) * len(baseline)) - 1)


def robust_z(baseline: np.ndarray, values: Series) -> dict[date, float]:
    """Robust z-score relative to the baseline median and MAD: 0.6745 (x - median) / MAD. Empty result when MAD = 0."""
    med = float(np.median(baseline))
    mad = float(np.median(np.abs(baseline - med)))
    return {d: 0.6745 * (v - med) / mad for d, v in values.items()} if mad > 0 else {}


def lagged_spearman(a: Series, b: Series, lag: int) -> tuple[int, float, float] | None:
    """Spearman correlation of a(D) with b(D + lag days): (n, rho, p), or None if constant or <10 pairs."""
    pairs = [(v, b[d + timedelta(days=lag)]) for d, v in a.items() if d + timedelta(days=lag) in b]
    if len(pairs) < 10:
        return None
    xs, ys = np.array(pairs).T
    if np.ptp(xs) == 0 or np.ptp(ys) == 0:
        return None
    res = stats.spearmanr(xs, ys)
    return len(pairs), float(res.statistic), float(res.pvalue)


def kruskal_by_group(
    values: Series, groups: dict[date, str], min_per_group: int = 3
) -> tuple[float, dict[str, float]] | None:
    """Kruskal-Wallis: whether values differ between groups (e.g. cycle phases). Returns (p, group medians) or None
    when, after dropping groups smaller than `min_per_group`, fewer than 2 groups remain or all values are equal."""
    by: dict[str, list[float]] = {}
    for d, v in values.items():
        if d in groups:
            by.setdefault(groups[d], []).append(v)
    by = {g: vs for g, vs in by.items() if len(vs) >= min_per_group}
    if len(by) < 2 or np.ptp(np.concatenate(list(by.values()))) == 0:
        return None
    return float(stats.kruskal(*by.values()).pvalue), {g: float(np.median(vs)) for g, vs in by.items()}

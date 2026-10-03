# statistics: trend detection in health data

The module computes deterministic statistics from the health tables (`vital_samples`, `daily_summaries`, `blood_pressure_readings`,
`ecg_recordings`, `cycle_days`). Its result (a JSON-serializable dict) feeds the doctor's report and the AI model context.
The AI model **does not compute** trends; it only describes the finished table.

The folder lives in `app/` (import `app.statistics`) rather than `backend/statistics/`: a directory named `statistics` in the
working directory would shadow the standard library `statistics` module.

```python
from app.statistics import analyze

result = analyze(db, user_id)  # last 60 full UTC days (up to yesterday)
result = analyze(db, user_id, end=date(2026, 6, 30), days=40)
```

**Everything is computed per person.** `analyze(db, user_id)` takes the data of one user; baselines, tests and the multiple-comparison
correction (`p_adj`) concern only that user's series. Nothing is aggregated across people, and the doctor's report
is built from a single `analyze` result for a single patient.

Flow: `daily.py` (raw measurements → 1 value per day) → `trends.py` (tests) → `analyze.py` (assembles the result, multiple-testing correction).
Raw samples are not tested directly: they have a daily rhythm and are autocorrelated, which yields falsely small p-values.

## Files and functions

### `daily.py`
- `Series`: `dict[date, float]`; days without data are absent from the dict.
- `daily_features(db, user_id, start, end)`: daily (UTC) features for days `start`..`end` inclusive. A feature is not produced when the day has too few samples
  (`MIN_SAMPLES = 12` in the hour window). Returned features:

| Feature | Definition |
|---|---|
| `rhr` | 10th percentile of heart rate between 00–06 h (resting heart rate) |
| `night_dip` | mean heart rate 08–20 minus mean 00–06 (loss of the nocturnal dip is clinically significant) |
| `stress_day_mean` | mean stress 08–20 |
| `stress_high_frac` | fraction of stress samples >60 between 08–20 h |
| `spo2_min` | minimum SpO₂ of the day |
| `spo2_low_count` | number of SpO₂ samples <94% |
| `bp_sys`, `bp_dia` | daily mean systolic and diastolic blood pressure |
| `bp_am_pm_diff` | systolic in the morning (<12) minus evening (≥17) |
| `bp_sys_sd_wk` | standard deviation of `bp_sys` in non-overlapping 7-day blocks counted backwards from `end` (min. 4 values per block, only full blocks in the window); 1 point per week, i.e. blood pressure variability |
| `steps`, `sleep_minutes` | values from `daily_summaries` |
| `ecg_hr` | mean heart rate from the day's ECG recordings |
| `ecg_abnormal` | 1 when any ECG classification ≠ `sinus_rhythm`, otherwise 0 |

- `weekly_sd(daily, start, end, window=7, min_n=4)`: standard deviation (ddof=1) in non-overlapping blocks of `window` days; the value sits on the last day of the block. Blocks must not overlap because a rolling window produced false trends.
- `cycle_phases(db, user_id, start, end)`: cycle phase per day; empty dict for users without a cycle (e.g. men).

### `trends.py` (pure numpy/scipy functions, no database)
- `sen_slope(x, y)`: Sen slope (median of pairwise slopes) + 95% CI. Robust to outliers.
- `mann_kendall(x, y)`: p-value of the monotonic trend test with Hamed–Rao autocorrelation correction (variance factor ≥ 1, so the correction
  can only tighten). Returns 1.0 for a constant series.
- `pettitt(y)`: most likely single change point (index of the first point of the new regime) and p-value.
- `compare(baseline, recent)`: Mann–Whitney U, returns the p-value and Cliff's delta (−1..1; positive = recent days higher than baseline).
- `robust_z(baseline, values)`: robust z-score `0.6745·(x − median)/MAD` relative to the baseline; empty result when MAD = 0.
- `lagged_spearman(a, b, lag)`: Spearman correlation of `a(D)` with `b(D+lag)`; `None` when there are <10 pairs or a series is constant.
- `kruskal_by_group(values, groups)`: Kruskal–Wallis between groups (cycle phases), groups with <3 days are skipped; `None` when <2 groups remain.

### `analyze.py`
- `analyze_series(series, end)`: tests of a single metric. Result is `status: "insufficient_data"` (n < 28 days) or `ok` with the fields `trend`
  (`slope_per_week`, `ci95_per_week`, `p`), `change_point` (`date`, medians before/after, `p`), `baseline_vs_recent`
  (medians, `delta`, `cliffs_delta`, `p`) and `outlier_days` (days from the last 7 with |z| > 2).
- `analyze(db, user_id, end=None, days=60)`: all metrics from `METRICS`, lagged correlations (`LAG_PAIRS` × lag 0–2 days: sleep→RHR,
  sleep→stress, steps→RHR) and the effect of cycle phase on `rhr` and `stress_day_mean`. Adds `p_adj` (Benjamini–Hochberg) to every `p`, separately within
  each test family (trend, change point, baseline-vs-recent, correlations, cycle).

### `charts.py` (charts for the PDF: matplotlib + seaborn, static)
Everything takes the result of `analyze(..., include_series=True)` and returns a `matplotlib.figure.Figure` (or `None` when there is nothing to draw).
Figures are built without `pyplot`, so there is no global state or GUI; width = A4 (8.27 in).
- `plot_metric(name, r)`: daily series of one metric with marked: baseline window (grey) and last 7 days (orange) with
  medians and Δ, Sen trend line (solid red = significant after correction, dashed grey = not significant; the subtitle shows slope,
  95% CI, `p_adj`), significant change point (purple vertical + medians before/after), outlier days |z| > 2 (red dots)
  and clinical threshold (`REFERENCE`: SpO₂ 94, blood pressure 135/85, sleep 6 h). For `insufficient_data` it draws only the series with an annotation.
- `plot_significance(result)`: bars of −log10(`p_adj`) of each metric's trend against the 0.05 threshold (an overview of "what is significant").
- `plot_correlations(result)`: heatmap of Spearman correlations with a 0–2 day lag, `*` = `p_adj` < 0.05.
- `plot_cycle(result)`: metric medians by cycle phase (points, axis not from zero), Kruskal–Wallis `p_adj` in the title.
- `figures(result)`: list of `(name, Figure)` in order: significance, correlations, cycle, then each metric from `METRICS`.
- `render_pdf(result, dest)`: PDF (path or `BytesIO`), one page per chart. `to_png(fig, dpi=150)`: PNG bytes of a single chart.
- `LABELS` (English names and units) and `REFERENCE` (thresholds) are the only place to edit when adding a new metric.

```python
from app.statistics import analyze
from app.statistics.charts import render_pdf, figures, to_png
result = analyze(db, user_id, include_series=True)
render_pdf(result, "report_charts.pdf")          # or: for name, fig in figures(result): to_png(fig)
```

### Chart data and endpoint
- `analyze(..., include_series=True)` adds to every metric `series` (`[{date, value}]`, also for `insufficient_data`) and `trend_line`
  (two points of the Sen line: first and last day). `baseline_vs_recent` always contains `baseline_window` and `recent_window`.
  Without this flag the result is compact (suitable for the AI model context).
- `GET /api/v1/health/stats?days=60&end=YYYY-MM-DD` (`router_charts.py`, JWT, data of the logged-in user): the same with `include_series=True`.
  `days` 7–365, default 60 (≈40 KB of JSON). **Note:** `app/api/v1/router.py` imports `charts`, while the file is named `router_charts.py`, so
  until this is reconciled the application will not start and the endpoint is not registered.
- `GET /api/v1/health/report` (`health.py`, JWT): PDF with charts (`render_pdf`) for the logged-in user, default window as in `analyze`.
  Without a token 401; when no metric has status `ok` (too little data) 422 with a message.
  `curl -H "Authorization: Bearer <token>" -o report.pdf http://localhost:8000/api/v1/health/report`

### Windows and minimums (constants in `analyze.py`)
- Trend and change point: all days of the window (default 60), minimum **28 days with data** (`bp_sys_sd_wk`: **8 weekly points**, i.e. 56 days; `MIN_POINTS` in `analyze.py`). Fewer: `insufficient_data`, which is different from "no trend".
- "Recent": 7 days up to and including `end` (min. 4 with data). Baseline: the 28 days directly before them (min. 14 with data).
- The default generator (`--days 7`) is too short: analysis needs e.g. `--days 60`.
- Women: ideally ≥ 1 full cycle of data, so that the luteal phase is not mistaken for a trend.

## Clinical thresholds for the report (NOT YET IMPLEMENTED, the report will be built last)

A change goes into the report when it is statistically significant (`p_adj` < 0.05) **and** exceeds the clinical threshold:

| Metric | Clinical threshold |
|---|---|
| RHR (`rhr`) | rise ≥ 5 bpm relative to baseline or slope ≥ 1 bpm/week |
| Blood pressure (`bp_sys`, `bp_dia`; home measurements, ESC) | mean ≥ 135/85 mmHg; increasing variability (`bp_sys_sd_wk`) |
| SpO₂ (`spo2_min`, `spo2_low_count`) | repeated values < 94%, especially at night |
| Sleep (`sleep_minutes`) | mean < 6 h (360 min) or large irregularity |
| ECG (`ecg_abnormal`) | ≥ 2 episodes of bradycardia or tachycardia in 30 days |
| Nocturnal heart rate dip (`night_dip`) | loss |

Per-metric report: baseline → last 7 days → change → slope per week [95% CI] → `p_adj` → change point date → clinical flag;
plus a separate section of lagged correlations and an explicit "no significant changes" entry for the remaining metrics.

Not yet implemented: heart rate cosinor (level, amplitude, peak hour), HRV (the current ECG waveform has a constant R–R interval).

## Tests

`pytest tests/test_statistics.py` (the whole thing with `--noconftest`, because `tests/conftest.py` loads `app.main`; see the note on `router.py`): trend detection and its CI, change point date, white noise (false-trend rate ≈ 5%), outlier-day flag,
`insufficient_data`, end-to-end run with SQLite, and `include_series` plus PDF rendering (5 pages, JSON-serializability).

## Validation on generator data (smoke, 60 days, SQLite)

One-off test on `Person.day_payload()` from `generator/generate.py`; 12 people without a trend (negative control) and 3 with an injected
trend. People are only repetitions here; each analysis is independent.

- **Negative control:** 168 trend tests, p < 0.05 before correction in 13 (7.7%), after BH correction in 3. Per person: 2 of 12 would get
  a false flag in the report (`bp_sys_sd_7d`, rolling window, since replaced by `bp_sys_sd_wk`; one also had `stress_high_frac`). Lagged correlations and cycle: 0 false hits.
- **Injected trend** (`rhr` +0.84/week, stress +1.4/week, sleep −14 min/week, systolic +1.4 mmHg/week): detected in all 3 people with slopes consistent
  with the injected ones (the 95% CI covers them); steps without a trend stayed non-significant (`p_adj` 0.33–0.80).
  `rhr` comes out slightly below 0.84 because it is the 10th percentile of heart rate, not the mean.

## Known limitations

- **`bp_sys_sd_wk`** has only 8 points per 60 days, so the trend test has limited power: it detects a strong rise in variability (SD 3→18 mmHg) in about 72% of series and may miss a weak one. False trends: ≈3% (negative control, 2000 series). The earlier 7-day rolling window gave ≈17% (overlapping data), hence it was replaced by blocks. `baseline_vs_recent` and `outlier_days` for this feature are empty (1 point in the last week).
- Features derived from the same series (`stress_day_mean` and `stress_high_frac`, `bp_sys` and `bp_sys_sd_wk`) are not independent tests,
  while the BH correction treats them as independent.
- Pettitt returns a single change point (the largest); the p-value is approximate.

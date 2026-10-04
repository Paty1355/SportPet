# statistics: trend detection in health data

This module computes deterministic statistics from the health tables (`vital_samples`, `daily_summaries`, `blood_pressure_readings`,
`ecg_recordings`, `cycle_days`). Its result (a JSON-serializable dict) feeds the doctor's report and the AI model's context.
The AI model **does not compute** trends; it only describes the finished table.

The folder lives in `app/` (import `app.statistics`), not in `backend/statistics/`: a directory named `statistics` in the working
directory would shadow the standard library `statistics` module.

```python
from app.statistics import analyze

result = analyze(db, user_id)  # last 60 full UTC days (up to yesterday)
result = analyze(db, user_id, end=date(2026, 6, 30), days=40)
```

**Everything is computed per person.** `analyze(db, user_id)` takes the data of one user; baselines, tests and the multiple-comparison
correction (`p_adj`) concern only their series. Nothing is aggregated across people, and the doctor's report is built from a single
`analyze` result for a single patient.

Flow: `daily.py` (raw measurements → 1 value per day) → `trends.py` (tests) → `analyze.py` (assembles the result, multiple-testing correction).
Raw samples are not tested directly: they have a daily rhythm and are autocorrelated, which gives falsely small p-values.

## Files and functions

### `daily.py`
- `Series`: `dict[date, float]`; days without data are absent from the dict.
- `daily_features(db, user_id, start, end)`: daily (UTC) features for days `start`..`end` inclusive. A feature is not produced when a day has too few samples
  (`MIN_SAMPLES = 12` in the hour window). Returned features:

| Feature | Definition |
|---|---|
| `rhr` | 10th percentile of heart rate between 00:00 and 06:00 (resting heart rate) |
| `night_dip` | mean heart rate 08–20 minus mean 00–06 (loss of the nocturnal dip is clinically significant) |
| `stress_day_mean` | mean stress 08–20 |
| `stress_high_frac` | fraction of stress samples >60 between 08 and 20 |
| `spo2_min` | minimum SpO₂ of the day |
| `spo2_low_count` | number of SpO₂ samples <94% |
| `bp_sys`, `bp_dia` | daily mean systolic and diastolic blood pressure |
| `bp_am_pm_diff` | systolic in the morning (<12) minus in the evening (≥17) |
| `bp_sys_sd_wk` | standard deviation of `bp_sys` in non-overlapping 7-day blocks counted back from `end` (min. 4 values per block, only full blocks in the window); 1 point per week, i.e. blood-pressure variability |
| `steps`, `sleep_minutes` | values from `daily_summaries` |
| `ecg_hr` | mean pulse from the day's ECG recordings |
| `ecg_abnormal` | 1 when any ECG classification ≠ `sinus_rhythm`, otherwise 0 |

- `weekly_sd(daily, start, end, window=7, min_n=4)`: standard deviation (ddof=1) in non-overlapping blocks of `window` days; the value sits on the last day of the block. Blocks must not overlap, because a rolling window produced false trends.
- `cycle_phases(db, user_id, start, end)`: cycle phase per day; an empty dict for users without a cycle (e.g. men).

### `trends.py` (pure numpy/scipy functions, no database)
- `sen_slope(x, y)`: Sen's slope (median of pairwise slopes) + 95% CI. Robust to outliers.
- `mann_kendall(x, y)`: p-value of the monotonic-trend test with Hamed–Rao autocorrelation correction (variance factor ≥ 1, so the correction
  only tightens). Returns 1.0 for a constant series.
- `pettitt(y)`: the most likely single change point (index of the first point of the new regime) and its p-value.
- `compare(baseline, recent)`: Mann–Whitney U, returns the p-value and Cliff's delta (−1..1; positive = recent days larger than the baseline).
- `robust_z(baseline, values)`: robust z-score `0.6745·(x − median)/MAD` relative to the baseline; empty result when MAD = 0.
- `lagged_spearman(a, b, lag)`: Spearman correlation of `a(D)` with `b(D+lag)`; `None` when there are <10 pairs or a series is constant.
- `kruskal_by_group(values, groups)`: Kruskal–Wallis across groups (cycle phases), groups with <3 days are dropped; `None` when <2 groups remain.

### `analyze.py`
- `analyze_series(series, end)`: tests for one metric. The result is `status: "insufficient_data"` (n < 28 days) or `ok` with the fields `trend`
  (`slope_per_week`, `ci95_per_week`, `p`), `change_point` (`date`, medians before/after, `p`), `baseline_vs_recent`
  (medians, `delta`, `cliffs_delta`, `p`) and `outlier_days` (days from the last 7 with |z| > 2).
- `analyze(db, user_id, end=None, days=60)`: all metrics from `METRICS`, lagged correlations (`LAG_PAIRS` × lag 0–2 days: sleep→RHR,
  sleep→stress, steps→RHR) and the effect of the cycle phase on `rhr` and `stress_day_mean`. Adds `p_adj` (Benjamini–Hochberg) to every `p`, separately in
  each test family (trend, change point, baseline-vs-recent, correlations, cycle).
- `detect_overtraining(metrics)`: pure function over `analyze()["metrics"]` (after `p_adj` correction), called by `analyze`. See "Overtraining flag".

### Overtraining flag (`result["overtraining"]`)
`analyze(...)` always adds an `overtraining` key (also in `GET /api/v1/health/stats`), so the frontend only needs to check
`result.overtraining.flag`:

```json
{"flag": true, "signals": [{"metric": "rhr", "delta": 8.0, "slope_per_week": 1.9}, {"metric": "sleep_minutes", "delta": -70.0, "slope_per_week": -22.0}]}
```

- `flag`: `true` when there is an `rhr` signal **and** at least one other signal. A rise in RHR alone (illness, caffeine) or worse sleep alone is not enough.
- `signals`: detected signals (use them for the notification text). `delta` = median of the last 7 days minus the baseline (`null` when that comparison has no data), `slope_per_week` = Sen slope.
- A signal = a change that is significant after correction (`p_adj` < 0.05) **and** beyond the threshold in the bad direction. Either is enough:
  `baseline_vs_recent` (median of the last 7 days minus the 28 days before ≥ min `delta`) or `trend` (slope over the whole window ≥ min slope):

| Metric | Bad change | Min `delta` | Min slope/week |
|---|---|---|---|
| `rhr` | increase | 5 bpm | 1 bpm |
| `night_dip` | decrease (loss of the nocturnal heart-rate dip) | 3 bpm | 1 bpm |
| `stress_day_mean` | increase | 5 | 2 |
| `sleep_minutes` | decrease | 30 min | 15 min |

- `flag` is `false` when: only the `rhr` signal is present, or only other signals without `rhr`; a change is significant but below the threshold
  (or above the threshold but not significant after `p_adj`); a metric is `insufficient_data` (the daily series needs ≥ 28 days with data), so with
  no data the result is `{"flag": false, "signals": []}`.
- `signals` lists all detected signals even when `flag` is `false` (e.g. `rhr` alone), so the frontend can show them separately from the overtraining notification.
- Thresholds (`OVERTRAINING` in `analyze.py`) are heuristics: `rhr` comes from the clinical thresholds below, the rest were hand-picked. HRV, the best
  overtraining marker, is not available (the ECG wave has a constant R–R interval). Training load (steps) is not counted as a signal.

### `charts.py` (charts for the PDF: matplotlib + seaborn, static)
Everything takes the result of `analyze(..., include_series=True)` and returns a `matplotlib.figure.Figure` (or `None` when there is nothing to draw).
Figures are created without `pyplot`, so there is no global state or GUI; width = A4 (8.27 in).
- `plot_metric(name, r)`: the daily series of one metric with marked: the baseline window (grey) and the last 7 days (orange) with
  medians and Δ, the Sen trend line (solid red = significant after correction, dashed grey = not significant; the subtitle shows the slope,
  95% CI, `p_adj`), a significant change point (purple vertical line + medians before/after), outlier days |z| > 2 (red dots)
  and the clinical threshold (`REFERENCE`: SpO₂ 94, blood pressure 135/85, sleep 6 h). For `insufficient_data` it draws only the series with an annotation.
- `plot_significance(result)`: bars of −log10(`p_adj`) of each metric's trend against the 0.05 threshold (an overview of "what is significant").
- `plot_correlations(result)`: heatmap of Spearman correlations with a lag of 0–2 days, `*` = `p_adj` < 0.05.
- `plot_cycle(result)`: medians of metrics across cycle phases (dots, axis not from zero), Kruskal–Wallis `p_adj` in the title.
- `figures(result)`: list of `(name, Figure)` in the order: significance, correlations, cycle, then each metric from `METRICS`.
- `render_pdf(result, dest)`: PDF (path or `BytesIO`), one page per chart. `to_png(fig, dpi=150)`: PNG bytes of a single chart.
- `LABELS` (Polish names and units) and `REFERENCE` (thresholds) are the only places to edit when adding a new metric.

```python
from app.statistics import analyze
from app.statistics.charts import render_pdf, figures, to_png

result = analyze(db, user_id, include_series=True)
render_pdf(result, "raport_wykresy.pdf")  # or: for name, fig in figures(result): to_png(fig)
```

### Chart data and endpoints
- `analyze(..., include_series=True)` adds to each metric `series` (`[{date, value}]`, also for `insufficient_data`) and `trend_line`
  (two points of the Sen line: first and last day). `baseline_vs_recent` always contains `baseline_window` and `recent_window`.
  Without this flag the result is compact (suitable for the AI model's context).
- `GET /api/v1/health/stats?days=60&end=YYYY-MM-DD` (`router_charts.py`, JWT, data of the logged-in user): the same with `include_series=True`.
  `days` 7–365, default 60 (≈40 KB of JSON). The router is registered in `app/api/v1/router.py`; the response includes `overtraining`.
- `GET /api/v1/health/report` (`health.py`, JWT): a PDF with charts (`render_pdf`) for the logged-in user, default window as in `analyze`.
  Without a token 401; when no metric has status `ok` (too little data) 422 with a message.
  `curl -H "Authorization: Bearer <token>" -o raport.pdf http://localhost:8000/api/v1/health/report`

### Windows and minimums (constants in `analyze.py`)
- Trend and change point: all days of the window (default 60), minimum **28 days with data** (`bp_sys_sd_wk`: **8 weekly points**, i.e. 56 days; `MIN_POINTS` in `analyze.py`). Fewer: `insufficient_data`, which is different from "no trend".
- "Recent": 7 days up to and including `end` (min. 4 with data). Baseline: the 28 days directly before them (min. 14 with data).
- The default generator (`--days 7`) is too short: the analysis needs e.g. `--days 60`.
- Women: ideally ≥ 1 full cycle of data, so the luteal phase is not mistaken for a trend.

## Clinical thresholds for the report (NOT IMPLEMENTED yet, the report will be built last)

The report includes a change that is statistically significant (`p_adj` < 0.05) **and** exceeds a clinical threshold:

| Metric | Clinical threshold |
|---|---|
| RHR (`rhr`) | rise ≥ 5 bpm relative to the baseline or slope ≥ 1 bpm/week |
| Blood pressure (`bp_sys`, `bp_dia`; home measurements, ESC) | mean ≥ 135/85 mmHg; increasing variability (`bp_sys_sd_wk`) |
| SpO₂ (`spo2_min`, `spo2_low_count`) | repeated values < 94%, especially at night |
| Sleep (`sleep_minutes`) | mean < 6 h (360 min) or large irregularity |
| ECG (`ecg_abnormal`) | ≥ 2 episodes of bradycardia or tachycardia in 30 days |
| Nocturnal heart-rate dip (`night_dip`) | loss |

Report per metric: baseline → last 7 days → change → slope per week [95% CI] → `p_adj` → change-point date → clinical flag;
plus a separate section of lagged correlations and an explicit "no significant changes" entry for the remaining metrics.

Not implemented yet: cosinor of heart rate (level, amplitude, peak hour), HRV (the current ECG wave has a constant R–R interval).

## Tests

`pytest tests/test_statistics.py` (everything with `--noconftest`, because `tests/conftest.py` loads `app.main`): trend detection and its CI, overtraining flag (RHR + a second signal), change-point date, white noise (share of false trends ≈ 5%), outlier-day flag,
`insufficient_data`, an end-to-end run with SQLite, and `include_series` plus PDF rendering (5 pages, JSON-serializability).

## Validation on generator data (smoke, 60 days, SQLite)

A one-off test on `Person.day_payload()` from `generator/generate.py`; 12 people without a trend (negative control) and 3 with an injected
trend. People here are just repetitions, each analysis is independent.

- **Negative control:** 168 trend tests, p < 0.05 in 13 before correction (7.7%), 3 after BH correction. Per person: 2 of 12 would get
  a false flag in the report (`bp_sys_sd_7d`, rolling window, since replaced by `bp_sys_sd_wk`; for one of them also `stress_high_frac`). Lagged correlations and cycle: 0 false hits.
- **Injected trend** (`rhr` +0.84/week, stress +1.4/week, sleep −14 min/week, systolic +1.4 mmHg/week): detected in all 3 people with slopes consistent with the injected ones
  (the 95% CI covers them); steps without a trend stayed non-significant (`p_adj` 0.33–0.80).
  `rhr` comes out slightly below 0.84, because it is the 10th percentile of heart rate, not the mean.

## Known limitations

- **`bp_sys_sd_wk`** has only 8 points per 60 days, so its trend test has limited power: it detects a strong rise in variability (SD 3→18 mmHg) in about 72% of series and may miss a weak one. False trends: ≈3% (negative control, 2000 series). The earlier 7-day rolling window gave ≈17% (overlapping data), which is why it was replaced with blocks. `baseline_vs_recent` and `outlier_days` for this feature are empty (1 point in the last week).
- Features derived from the same series (`stress_day_mean` and `stress_high_frac`, `bp_sys` and `bp_sys_sd_wk`) are not independent tests,
  and the BH correction treats them as independent.
- Pettitt returns one change point (the largest); the p-value is approximate.

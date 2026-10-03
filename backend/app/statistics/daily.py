"""Redukcja surowych pomiarów do jednej wartości na dobę (UTC). Surowe próbki mają rytm dobowy i są autokorelowane,
więc testy trendu robimy dopiero na tych szeregach dziennych."""

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BloodPressureReading, CycleDay, DailySummary, EcgRecording, VitalSample

Series = dict[date, float]  # doba -> wartość; doby bez danych po prostu nie występują

NIGHT = range(0, 6)  # godziny UTC do tętna spoczynkowego i nocnego spadku
DAY = range(8, 20)  # godziny UTC do wartości "dziennych"
MIN_SAMPLES = 12  # poniżej tylu próbek w oknie doby cecha nie jest liczona (puls i stres: 72 próbki w 6 h)
STRESS_HIGH = 60
SPO2_LOW = 94
SD_WINDOW_DAYS, SD_MIN_DAYS = 7, 4


def _utc(dt: datetime) -> datetime:
    # SQLite oddaje naive, Postgres aware
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    """[początek `start`, początek doby po `end`) w UTC, czyli `end` włącznie."""
    return datetime.combine(start, time.min, UTC), datetime.combine(end + timedelta(days=1), time.min, UTC)


def weekly_sd(daily: Series, start: date, end: date, window: int = SD_WINDOW_DAYS, min_n: int = SD_MIN_DAYS) -> Series:
    """Odchylenie standardowe (ddof=1) w NIENAKŁADAJĄCYCH się blokach `window` dób, liczonych wstecz od `end`.
    Wartość stoi na ostatniej dobie bloku; liczą się tylko pełne bloki w [`start`, `end`] z min. `min_n` wartościami.
    Bloki się nie nakładają, bo kroczące okno daje autokorelację, której test trendu nie neutralizuje."""
    out, block_end = {}, end
    while block_end - timedelta(days=window - 1) >= start:
        vals = [daily[d] for i in range(window) if (d := block_end - timedelta(days=i)) in daily]
        if len(vals) >= min_n:
            out[block_end] = float(np.std(vals, ddof=1))
        block_end -= timedelta(days=window)
    return out


def daily_features(db: Session, user_id: int, start: date, end: date) -> dict[str, Series]:
    """Cechy dzienne użytkownika dla dób `start`..`end` włącznie.

    heart_rate -> rhr (10. percentyl pulsu 00-06), night_dip (średnia 08-20 minus średnia 00-06),
    stress -> stress_day_mean, stress_high_frac (odsetek próbek >60, godz. 08-20),
    spo2 -> spo2_min, spo2_low_count (próbki <94), ciśnienie -> bp_sys, bp_dia (średnie dobowe),
    bp_am_pm_diff (skurczowe rano <12 minus wieczorem >=17), bp_sys_sd_wk (zmienność skurczowego w blokach tyg.),
    steps, sleep_minutes, ecg_hr (średni puls z EKG), ecg_abnormal (1 gdy klasyfikacja != sinus_rhythm)."""
    lo, hi = _bounds(start, end)
    out: dict[str, Series] = defaultdict(dict)

    vitals: dict[tuple[str, date], list[tuple[int, float]]] = defaultdict(list)
    for metric, ts, value in db.execute(
        select(VitalSample.metric, VitalSample.ts, VitalSample.value).where(
            VitalSample.user_id == user_id, VitalSample.ts >= lo, VitalSample.ts < hi
        )
    ):
        ts = _utc(ts)
        vitals[metric, ts.date()].append((ts.hour, value))

    def window(rows: list[tuple[int, float]], hours: range) -> list[float]:
        return [v for h, v in rows if h in hours]

    for (metric, day), rows in vitals.items():
        if metric == "heart_rate":
            night, daytime = window(rows, NIGHT), window(rows, DAY)
            if len(night) >= MIN_SAMPLES:
                out["rhr"][day] = float(np.percentile(night, 10))
                if len(daytime) >= MIN_SAMPLES:
                    out["night_dip"][day] = float(np.mean(daytime) - np.mean(night))
        elif metric == "stress":
            daytime = window(rows, DAY)
            if len(daytime) >= MIN_SAMPLES:
                out["stress_day_mean"][day] = float(np.mean(daytime))
                out["stress_high_frac"][day] = float(np.mean(np.array(daytime) > STRESS_HIGH))
        elif metric == "spo2" and len(rows) >= 4:
            values = [v for _, v in rows]
            out["spo2_min"][day] = float(min(values))
            out["spo2_low_count"][day] = float(sum(v < SPO2_LOW for v in values))

    bp: dict[date, list[BloodPressureReading]] = defaultdict(list)
    for r in db.scalars(
        select(BloodPressureReading).where(
            BloodPressureReading.user_id == user_id, BloodPressureReading.ts >= lo, BloodPressureReading.ts < hi
        )
    ):
        bp[_utc(r.ts).date()].append(r)
    for day, rs in bp.items():
        out["bp_sys"][day] = float(np.mean([r.systolic for r in rs]))
        out["bp_dia"][day] = float(np.mean([r.diastolic for r in rs]))
        am = [r.systolic for r in rs if _utc(r.ts).hour < 12]
        pm = [r.systolic for r in rs if _utc(r.ts).hour >= 17]
        if am and pm:
            out["bp_am_pm_diff"][day] = float(np.mean(am) - np.mean(pm))
    out["bp_sys_sd_wk"] = weekly_sd(out["bp_sys"], start, end)

    for r in db.scalars(
        select(DailySummary).where(DailySummary.user_id == user_id, DailySummary.date.between(start, end))
    ):
        if r.steps is not None:
            out["steps"][r.date] = float(r.steps)
        if r.sleep_minutes is not None:
            out["sleep_minutes"][r.date] = float(r.sleep_minutes)

    ecg: dict[date, list[EcgRecording]] = defaultdict(list)
    for r in db.scalars(
        select(EcgRecording).where(
            EcgRecording.user_id == user_id, EcgRecording.started_at >= lo, EcgRecording.started_at < hi
        )
    ):
        ecg[_utc(r.started_at).date()].append(r)
    for day, rs in ecg.items():
        out["ecg_hr"][day] = float(np.mean([r.avg_heart_rate for r in rs]))
        out["ecg_abnormal"][day] = float(any(r.classification != "sinus_rhythm" for r in rs))

    return dict(out)


def cycle_phases(db: Session, user_id: int, start: date, end: date) -> dict[date, str]:
    """Faza cyklu na dobę; pusty słownik dla użytkowników bez danych cyklu."""
    return dict(
        db.execute(
            select(CycleDay.date, CycleDay.phase).where(CycleDay.user_id == user_id, CycleDay.date.between(start, end))
        ).all()
    )

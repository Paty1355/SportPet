"""Synthetic health data generator (normal distribution) → FastAPI /api/v1/health/ingest.

    SERVICE_KEY=... uv run --with httpx generator/generate.py --api http://localhost:8000 --days 7 --seed 1

Generates data for EVERY active user from the users table (/health/service/* endpoints, X-Service-Key header).
A missing profile (sex, birth_date, weight_kg, height_cm) is filled in deterministically from (seed, user_id);
an existing profile is left untouched. The data is a SIMULATION, not clinical data.
--days N = the last N UTC days including today (today only up to the current moment).
"""

import argparse
import math
import os
import random
from datetime import UTC, date, datetime, timedelta

import httpx

SAMPLE_RATE_HZ = 512
ECG_SECONDS = 30


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def night_dip(hour: float) -> float:
    """0..1, maximum at 03:00 UTC, ~0 during the day. Lowers heart rate and stress at night."""
    return max(0.0, math.cos((hour - 3) / 24 * 2 * math.pi))


def ecg_wave(rng: random.Random, hr: float) -> list[float]:
    """PQRST template (sum of Gaussians in beat phase) + N(0, 0.02 mV) noise. The waveform itself is not normally distributed."""
    period = 60 / hr
    waves = [
        (0.20, 0.025, 0.15),
        (0.36, 0.008, -0.15),
        (0.40, 0.010, 1.0),
        (0.44, 0.010, -0.25),
        (0.65, 0.04, 0.30),
    ]
    out = []
    for i in range(SAMPLE_RATE_HZ * ECG_SECONDS):
        phase = (i / SAMPLE_RATE_HZ % period) / period
        v = sum(a * math.exp(-((phase - c) ** 2) / (2 * w * w)) for c, w, a in waves)
        out.append(round(v + rng.gauss(0, 0.02), 4))
    return out


def cycle_phase(day: int, length: int, period: int) -> str:
    ovulation_day = length - 14
    if day <= period:
        return "menstrual"
    if abs(day - ovulation_day) <= 1:
        return "ovulation"
    return "follicular" if day < ovulation_day else "luteal"


class Person:
    def __init__(self, profile: dict, rng: random.Random):
        self.rng = rng
        self.sex = profile["sex"]
        self.hr_mean = rng.gauss(70, 7)
        self.stress_mean = rng.gauss(40, 10)
        # cykl: zaczynamy w losowym dniu losowego cyklu
        self.cycle_length = self._new_cycle_length()
        self.period_length = int(clamp(round(rng.gauss(5, 1)), 2, 8))
        self.cycle_day = rng.randint(1, self.cycle_length)

    def _new_cycle_length(self) -> int:
        return int(clamp(round(self.rng.gauss(28, 2)), 21, 35))

    def day_payload(self, day: date) -> dict:
        r = self.rng
        midnight = datetime(day.year, day.month, day.day, tzinfo=UTC)
        samples = []
        for minutes in range(0, 24 * 60, 5):
            ts, dip = midnight + timedelta(minutes=minutes), night_dip(minutes / 60)
            hr = clamp(r.gauss(self.hr_mean - 8 * dip, 6), 35, 200)
            stress = clamp(r.gauss(self.stress_mean - 15 * dip, 12), 0, 100)
            samples.append(
                {"metric": "heart_rate", "ts": ts.isoformat(), "value": round(hr, 1)}
            )
            samples.append(
                {"metric": "stress", "ts": ts.isoformat(), "value": round(stress, 1)}
            )
            if minutes % 15 == 0:
                samples.append(
                    {
                        "metric": "spo2",
                        "ts": ts.isoformat(),
                        "value": round(clamp(r.gauss(97, 1), 90, 100), 1),
                    }
                )

        blood_pressure = []
        for hour in (8, 14, 20):
            diastolic = int(clamp(round(r.gauss(78, 7)), 40, 120))
            systolic = int(clamp(round(r.gauss(120, 10)), diastolic + 15, 220))
            blood_pressure.append(
                {
                    "ts": (midnight + timedelta(hours=hour)).isoformat(),
                    "systolic": systolic,
                    "diastolic": diastolic,
                }
            )

        ecg_hr = clamp(r.gauss(self.hr_mean, 6), 40, 180)
        ecg = {
            "started_at": (midnight + timedelta(hours=9)).isoformat(),
            "sample_rate_hz": SAMPLE_RATE_HZ,
            "avg_heart_rate": round(ecg_hr, 1),
            "classification": "bradycardia"
            if ecg_hr < 50
            else "tachycardia"
            if ecg_hr > 100
            else "sinus_rhythm",
            "samples": ecg_wave(r, ecg_hr),
        }
        payload = {
            "samples": samples,
            "daily": [
                {
                    "date": day.isoformat(),
                    "steps": int(max(0, r.gauss(8000, 2500))),
                    "sleep_minutes": int(clamp(r.gauss(430, 50), 120, 720)),
                }
            ],
            "blood_pressure": blood_pressure,
            "ecg": [ecg],
        }
        if self.sex == "F":
            payload["cycle"] = [
                {
                    "date": day.isoformat(),
                    "cycle_day": self.cycle_day,
                    "cycle_length": self.cycle_length,
                    "phase": cycle_phase(
                        self.cycle_day, self.cycle_length, self.period_length
                    ),
                }
            ]
            self.cycle_day += 1
            if self.cycle_day > self.cycle_length:
                self.cycle_day, self.cycle_length = 1, self._new_cycle_length()
        return payload


def random_profile(rng: random.Random, today: date) -> dict:
    female = rng.random() < 0.5
    age = clamp(rng.gauss(35, 12), 18, 80)
    return {
        "sex": "F" if female else "M",
        "birth_date": (today - timedelta(days=int(age * 365.25))).isoformat(),
        "weight_kg": round(
            clamp(rng.gauss(65 if female else 78, 11 if female else 12), 40, 140), 1
        ),
        "height_cm": round(
            clamp(rng.gauss(165 if female else 178, 6 if female else 7), 140, 205), 1
        ),
    }


def trim_to_now(payload: dict, now: datetime) -> dict:
    """Today: we generate the full payload (rng stream unchanged) but send only what has already happened.

    We do not send daily steps and sleep because writes are idempotent: a partial value from the first run would stay forever.
    """
    cutoff = now.replace(microsecond=0).isoformat()
    return {
        "samples": [x for x in payload["samples"] if x["ts"] <= cutoff],
        "blood_pressure": [x for x in payload["blood_pressure"] if x["ts"] <= cutoff],
        "ecg": [x for x in payload["ecg"] if x["started_at"] <= cutoff],
        **({"cycle": payload["cycle"]} if "cycle" in payload else {}),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument(
        "--key",
        default=os.environ.get("SERVICE_KEY"),
        help="X-Service-Key (domyślnie env SERVICE_KEY)",
    )
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--email", help="only this user (default all active users)")
    args = ap.parse_args()
    if not args.key:
        ap.error(
            "brak klucza: ustaw SERVICE_KEY albo --key (taki sam jak SERVICE_KEY backendu)"
        )

    now = datetime.now(UTC)
    today = now.date()
    days = [today - timedelta(days=d) for d in range(args.days - 1, -1, -1)]
    with httpx.Client(
        base_url=f"{args.api}/api/v1/health/service",
        headers={"X-Service-Key": args.key},
        timeout=60,
    ) as http:
        users = http.get("/users")
        users.raise_for_status()
        selected = [
            u
            for u in users.json()
            if args.email is None or u["email"] == args.email.lower()
        ]
        if not selected:
            ap.error(f"no active user {args.email}")
        for user in selected:
            rng = random.Random(args.seed * 1_000_003 + user["id"])
            wanted = random_profile(
                rng, today
            )  # zawsze losujemy, żeby strumień rng nie zależał od tego, co user już ma
            missing = {k: v for k, v in wanted.items() if user[k] is None}
            if missing:
                res = http.patch(f"/users/{user['id']}/profile", json=missing)
                res.raise_for_status()
                user = res.json()

            person = Person(user, rng)
            totals: dict[str, int] = {}
            for day in days:
                payload = person.day_payload(day)
                res = http.post(
                    f"/ingest/{user['id']}",
                    json=trim_to_now(payload, now) if day == today else payload,
                )
                res.raise_for_status()
                for k, v in res.json().items():
                    totals[k] = totals.get(k, 0) + v
            print(f"#{user['id']} {user['email']} ({user['sex']}): {totals}")


if __name__ == "__main__":
    main()

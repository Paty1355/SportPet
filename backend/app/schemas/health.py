from datetime import date, datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class SampleIn(BaseModel):
    metric: Literal["heart_rate", "spo2", "stress"]
    ts: AwareDatetime
    value: float

    @model_validator(mode="after")
    def value_in_range(self):
        lo, hi = {"heart_rate": (20, 250), "spo2": (50, 100), "stress": (0, 100)}[self.metric]
        if not lo <= self.value <= hi:
            raise ValueError(f"{self.metric} must be in [{lo}, {hi}]")
        return self


class DailyIn(BaseModel):
    date: date
    steps: int | None = Field(default=None, ge=0, le=200_000)
    sleep_minutes: int | None = Field(default=None, ge=0, le=24 * 60)


class BloodPressureIn(BaseModel):
    ts: AwareDatetime
    systolic: int = Field(ge=50, le=260)
    diastolic: int = Field(ge=30, le=160)

    @model_validator(mode="after")
    def systolic_above_diastolic(self):
        if self.systolic <= self.diastolic:
            raise ValueError("systolic must be greater than diastolic")
        return self


class EcgIn(BaseModel):
    started_at: AwareDatetime
    sample_rate_hz: int = Field(ge=50, le=2000)
    avg_heart_rate: float = Field(ge=20, le=250)
    classification: str = Field(max_length=32)
    samples: list[float] = Field(min_length=1, max_length=120_000)


class CycleIn(BaseModel):
    date: date
    cycle_day: int = Field(ge=1, le=60)
    phase: Literal["menstrual", "follicular", "ovulation", "luteal"]
    cycle_length: int = Field(ge=15, le=60)

    @model_validator(mode="after")
    def day_within_cycle(self):
        if self.cycle_day > self.cycle_length:
            raise ValueError("cycle_day must not exceed cycle_length")
        return self


class HealthIngest(BaseModel):
    """Wszystkie sekcje opcjonalne. Limity chronią przed pojedynczym ogromnym requestem."""

    samples: list[SampleIn] = Field(default_factory=list, max_length=5_000)
    daily: list[DailyIn] = Field(default_factory=list, max_length=400)
    blood_pressure: list[BloodPressureIn] = Field(default_factory=list, max_length=200)
    ecg: list[EcgIn] = Field(default_factory=list, max_length=10)
    cycle: list[CycleIn] = Field(default_factory=list, max_length=400)


class HealthIngestResult(BaseModel):
    """Liczba faktycznie zapisanych wierszy. Duplikaty (ten sam klucz) nie są liczone."""

    samples: int
    daily: int
    blood_pressure: int
    ecg: int
    cycle: int


# ---- odczyt (wykresy) ----


class SeriesPoint(BaseModel):
    ts: datetime
    value: float
    min: float | None = None  # tylko dla bucket != raw
    max: float | None = None


class SeriesOut(BaseModel):
    metric: str
    unit: str
    bucket: str
    start: datetime
    end: datetime
    points: list[SeriesPoint]


class DailyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    steps: int | None
    sleep_minutes: int | None


class BloodPressureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ts: datetime
    systolic: int
    diastolic: int


class CycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    cycle_day: int
    phase: str
    cycle_length: int


class EcgSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    sample_rate_hz: int
    avg_heart_rate: float
    classification: str


class LatestValue(BaseModel):
    ts: datetime
    value: float


class Dashboard(BaseModel):
    user_id: int
    name: str | None
    sex: str | None
    age: int | None
    weight_kg: float | None
    height_cm: float | None
    bmi: float | None
    latest: dict[str, LatestValue | None]  # heart_rate | spo2 | stress
    daily: list[DailyOut]
    blood_pressure: list[BloodPressureOut]
    cycle: list[CycleOut]  # empty for users without cycle data
    ecg: list[EcgSummary]  # without the waveform
    stats: dict  # `app.statistics.analyze(..., include_series=True)`

import datetime as dt

from app.schemas.feedback import FeedbackOut
from app.schemas.post_workout import CheckInResponse
from app.schemas.questionnaire import CamelModel


class PlanExercise(CamelModel):
    title: str
    gif_url: str
    description: str
    sets: int
    reps: int
    estimated_time_minutes: int


class Workout(CamelModel):
    day: str
    date: dt.date | None = None
    focus: str
    exercises: list[PlanExercise]


class HealthSummary(CamelModel):

    sex: str | None = None
    age: int | None = None
    bmi: float | None = None
    days_with_data: int = 0
    resting_heart_rate: int | None = None
    sleep_hours: float | None = None
    daily_steps: int | None = None
    stress: int | None = None
    blood_pressure_systolic: int | None = None
    blood_pressure_diastolic: int | None = None
    spo2_min: float | None = None
    abnormal_ecg_days: int = 0
    cycle_phase: str | None = None
    cycle_day: int | None = None
    cycle_length: int | None = None
    overtraining: bool = False
    overtraining_signals: list[str] = []
    mental_health_concern: bool = False


class TrainingPlan(CamelModel):
    workouts: list[Workout]
    health_summary: HealthSummary | None = None
    recent_feedback: list[FeedbackOut] = []


class WorkoutDone(CamelModel):
    plan: TrainingPlan
    check_in: CheckInResponse

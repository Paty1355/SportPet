from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

MainGoal = Literal["weight_loss", "toning", "postpartum", "general_fitness"]
ExperienceLevel = Literal["beginner", "returning", "intermediate", "regular"]
BodyPart = Literal["glutes", "core", "back_arms", "full_body"]
LikedExercise = Literal["weights", "machines", "cardio", "bodyweight"]
DislikedExercise = Literal["burpees", "running", "jumping", "heavy_squats"]
Injury = Literal["back", "knees", "diastasis"]
PreferredDays = Literal["mwf", "weekends", "any_weekdays", "flexible"]
Lifestyle = Literal["desk_stress", "active", "physical_work", "balanced"]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class IntensityCheck(CamelModel):
    cautious_start: bool
    notes: str = ""


class TrainingQuestionnaire(CamelModel):
    """Final questionnaire result; literals must match option values in `QUESTIONS` (excluding "none")."""

    main_goal: MainGoal
    experience_level: ExperienceLevel
    priority_body_parts: list[BodyPart]
    liked_exercises: list[LikedExercise]
    disliked_exercises: list[DislikedExercise]
    injuries_and_limitations: list[Injury]
    preferred_days: PreferredDays
    training_days_per_week: int
    workout_duration_minutes: Literal[40, 60, 90]
    lifestyle_and_stress: Lifestyle
    intensity_check: IntensityCheck


class OptionOut(BaseModel):
    value: str
    label: str


class QuestionOut(BaseModel):
    key: str
    text: str
    options: list[OptionOut]
    multi: bool


class QuestionnaireStatus(CamelModel):
    step: int
    total: int
    completed: bool
    question: QuestionOut | None = None  # current question, None once completed
    training_questionnaire: TrainingQuestionnaire | None = None  # final result, set once completed

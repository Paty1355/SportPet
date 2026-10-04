from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator
from pydantic.alias_generators import to_camel

Period = Literal["daily", "weekly", "monthly"]
Score = Annotated[StrictInt, Field(ge=0, le=10)]
FeelingChange = Literal["better", "same", "worse"]
SafetyCode = Literal[
    "chest_discomfort",
    "severe_breathlessness",
    "fainting",
    "self_harm_risk",
    "worsening_pain",
    "movement_limited",
    "persistent_distress",
]


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class StartCheckIn(ApiModel):
    request_id: UUID
    workout_ended_at: AwareDatetime | None = None
    workout_type: str | None = Field(default=None, min_length=1, max_length=80)
    workout_duration_minutes: int | None = Field(default=None, ge=1, le=600)


class ChatTurn(ApiModel):
    request_id: UUID
    expected_version: int = Field(ge=0)
    action: Literal["answer", "skip", "correct", "confirm", "retry_support"] = "answer"
    message: str | None = Field(default=None, max_length=4000)
    field_key: str | None = None

    @model_validator(mode="after")
    def action_fields(self):
        if self.action in {"answer", "correct"} and (not self.message or not self.message.strip()):
            raise ValueError("message is required for answer/correct")
        if self.action == "correct" and not self.field_key:
            raise ValueError("fieldKey is required for correct")
        if self.action != "correct" and self.field_key is not None:
            raise ValueError("fieldKey is only accepted for correct")
        if self.action in {"skip", "confirm", "retry_support"} and self.message is not None:
            raise ValueError("this action does not accept message")
        return self


class PainFeedback(ApiModel):
    experienced: bool | None
    intensity: Score | None
    locations: list[str]
    description: str | None

    @model_validator(mode="after")
    def consistent_pain(self):
        if self.experienced is not True and (self.locations or self.description):
            raise ValueError("pain details require experienced=true")
        if self.experienced is False and self.intensity != 0:
            raise ValueError("no pain must have intensity=0")
        if self.experienced is None and self.intensity is not None:
            raise ValueError("unknown pain must not have an intensity")
        return self


class PostWorkoutFeedback(ApiModel):
    workout_ended_at: datetime
    workout_type: str | None
    workout_duration_minutes: int | None
    fatigue_level: Score | None
    feeling_change: FeelingChange | None
    mood_level: Score | None
    motivation_level: Score | None
    perceived_exertion_rating: Score | None
    pain: PainFeedback


class QuestionOption(ApiModel):
    value: str
    label: str


class CheckInQuestion(ApiModel):
    key: str
    text: str
    type: Literal["scale", "choice", "text"]
    options: list[QuestionOption] = Field(default_factory=list)
    min_value: int | None = None
    max_value: int | None = None
    skippable: bool = True


class SafetyObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    code: SafetyCode
    evidence: str

    @field_validator("evidence")
    @classmethod
    def evidence_is_nonempty(cls, value: str) -> str:
        if not value.strip() or len(value) > 1000:
            raise ValueError("evidence must be a short nonempty quotation")
        return value.strip()


class SafetyNotice(ApiModel):
    level: Literal["consultation", "urgent"]
    codes: list[str]
    message: str


class Support(ApiModel):
    status: Literal["pending", "available", "unavailable"]
    message: str
    observations: list[str] = Field(default_factory=list)
    started_at: datetime | None = None


class CheckInResponse(ApiModel):
    session_id: str
    version: int
    status: Literal["in_progress", "awaiting_confirmation", "completed", "interrupted"]
    step: int
    total: int
    reply: str
    question: CheckInQuestion | None
    draft_feedback: PostWorkoutFeedback
    post_workout_feedback: PostWorkoutFeedback | None
    notice: SafetyNotice | None
    support: Support | None
    report_id: str | None = None


class CheckInMessage(ApiModel):
    role: str
    content: str
    created_at: datetime


class MetricComparison(ApiModel):
    count: int
    median: float | None
    previous_count: int
    previous_median: float | None
    delta: float | None
    status: Literal["ok", "insufficient_data"]


class PainStatistics(ApiModel):
    answered_count: int
    reported_count: int


class ReportStatistics(ApiModel):
    sample_count: int
    previous_sample_count: int
    status: Literal["ok", "insufficient_data"]
    metrics: dict[str, MetricComparison]
    feeling_change: dict[str, int]
    pain: PainStatistics


class ReportRequest(ApiModel):
    period: Period | None = None
    anchor_date: date | None = None
    regenerate_comment: bool = False


class Observation(ApiModel):
    id: str
    text: str


class ReportResponse(ApiModel):
    id: str
    period: Period
    timezone: str
    period_start: date
    period_end: date
    is_partial: bool
    computed_at: datetime
    analysis_version: str
    statistics: ReportStatistics
    observations: list[Observation]
    support: Support | None


class AnswerExtraction(BaseModel):
    """No numeric constraints in the wire schema; validate extracted scores locally too."""

    model_config = ConfigDict(extra="forbid", strict=True)
    score: int | None
    choice: Literal["yes", "no", "better", "same", "worse"] | None
    locations: list[str]
    text: str | None
    needs_clarification: bool
    safety_observations: list[SafetyObservation]

    @field_validator("score")
    @classmethod
    def score_in_range(cls, value: int | None) -> int | None:
        if value is not None and not 0 <= value <= 10:
            raise ValueError("score must be between 0 and 10")
        return value

    @field_validator("locations")
    @classmethod
    def nonempty_locations(cls, values: list[str]) -> list[str]:
        if len(values) > 10 or any(not value.strip() or len(value) > 80 for value in values):
            raise ValueError("invalid locations")
        return list(dict.fromkeys(value.strip() for value in values))


class SupportText(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    message: str
    observation_ids: list[str]

    @field_validator("message")
    @classmethod
    def short_message(cls, value: str) -> str:
        if not value.strip() or len(value) > 800:
            raise ValueError("message must be nonempty and no longer than 800 characters")
        return value.strip()

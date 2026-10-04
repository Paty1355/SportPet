from datetime import datetime
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from app.schemas.questionnaire import CamelModel

Score = Annotated[int, Field(ge=1, le=10)]


class PostWorkoutFeedback(CamelModel):
    fatigue_level: Score
    feeling_trend: Literal["better", "same", "worse"]
    motivation_level: Score
    pain_experienced: Literal["none", "mild", "moderate", "severe"]
    perceived_exertion_rating: Score
    reporting_frequency: Literal["after_each_workout", "weekly"]


class FeedbackIn(CamelModel):
    post_workout_feedback: PostWorkoutFeedback


class FeedbackOut(PostWorkoutFeedback):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime

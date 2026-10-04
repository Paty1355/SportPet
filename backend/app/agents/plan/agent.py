import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient, get_llm
from app.agents.plan import prompts
from app.agents.plan.descriptions import describe_exercises
from app.agents.plan.exercises import allowed_exercises, exercise_title, gif_url
from app.agents.plan.health import WINDOW_DAYS, health_summary
from app.core.config import settings
from app.models import User, WorkoutFeedback
from app.rag.knowledge_base import KnowledgeBase
from app.schemas.feedback import FeedbackOut, PostWorkoutFeedback
from app.schemas.plan import PlanExercise, TrainingPlan, Workout
from app.schemas.questionnaire import CamelModel, TrainingQuestionnaire

# Lengths must match DAYS_PER_WEEK in the questionnaire.
PLAN_DAYS = {
    "mwf": ["Monday", "Wednesday", "Friday"],
    "weekends": ["Saturday", "Sunday"],
    "any_weekdays": ["Monday", "Wednesday", "Friday"],
    "flexible": ["Day 1", "Day 2", "Day 3"],
}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
FLEXIBLE_GAP_DAYS = 2
FEEDBACK_LIMIT = 5


class PlanGenerationError(Exception):
    pass


class LlmExercise(CamelModel):
    name: str
    sets: int
    reps: int
    estimated_time_minutes: int


class LlmWorkout(CamelModel):
    focus: str = ""
    exercises: list[LlmExercise]


class LlmPlan(CamelModel):
    workouts: list[LlmWorkout]


class PlanAgent:
    """Weekly training plan: the LLM picks exercises from the available gifs, then descriptions come from RAG.

    Inputs: the questionnaire, recent health data and post-workout feedback."""

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.knowledge = KnowledgeBase("training")

    async def generate(
        self, db: Session, user: User, questionnaire: TrainingQuestionnaire, today: date | None = None
    ) -> TrainingPlan:
        health = health_summary(db, user)
        feedback = self.get_feedback(db, user.id, limit=FEEDBACK_LIMIT)
        allowed = allowed_exercises(questionnaire)
        days = PLAN_DAYS[questionnaire.preferred_days]
        system = prompts.SYSTEM_PROMPT.format(
            count=len(days),
            days=", ".join(days),
            minutes=questionnaire.workout_duration_minutes,
            catalogue="\n".join(f"- {name}" for name in allowed),
        )
        user_message = prompts.USER_MESSAGE.format(
            questionnaire=questionnaire.model_dump_json(by_alias=True, indent=2),
            window=WINDOW_DAYS,
            health=health.model_dump_json(by_alias=True, indent=2),
            feedback=json.dumps(
                [f.model_dump(mode="json", by_alias=True, exclude={"reporting_frequency"}) for f in feedback], indent=2
            ),
        )
        raw = await self.llm.complete(system, [{"role": "user", "content": user_message}], json_mode=True)
        selection = parse_selection(raw, len(days), set(allowed))

        names = list(dict.fromkeys(e.name for w in selection for e in w.exercises))
        descriptions = await describe_exercises(self.llm, self.knowledge, names)

        dates = plan_dates(days, today or date.today())
        workouts = [
            Workout(
                day=day,
                date=day_date,
                focus=w.focus,
                exercises=[
                    PlanExercise(
                        title=exercise_title(e.name),
                        gif_url=gif_url(e.name),
                        description=descriptions.get(e.name, ""),
                        sets=e.sets,
                        reps=e.reps,
                        estimated_time_minutes=e.estimated_time_minutes,
                    )
                    for e in w.exercises
                ],
            )
            for day, day_date, w in zip(days, dates, selection, strict=True)
        ]
        plan = TrainingPlan(workouts=workouts, health_summary=health, recent_feedback=feedback)
        self.plan_path(user.id).write_text(plan.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
        return plan

    def save_feedback(self, db: Session, user_id: int, feedback: PostWorkoutFeedback) -> FeedbackOut:
        row = WorkoutFeedback(user_id=user_id, **feedback.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return FeedbackOut.model_validate(row)

    def get_feedback(self, db: Session, user_id: int, limit: int) -> list[FeedbackOut]:
        """Newest first."""
        rows = db.scalars(
            select(WorkoutFeedback)
            .where(WorkoutFeedback.user_id == user_id)
            .order_by(WorkoutFeedback.id.desc())
            .limit(limit)
        )
        return [FeedbackOut.model_validate(r) for r in rows]

    def get(self, user_id: int) -> TrainingPlan | None:
        path = self.plan_path(user_id)
        if not path.exists():
            return None
        try:
            return TrainingPlan.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError:
            return None  # saved in an older format; the user has to generate a new plan

    def plan_path(self, user_id: int) -> Path:
        path = Path(settings.training_plan_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{user_id}.json"


def plan_dates(days: list[str], today: date) -> list[date]:
    """Nearest date (today included) for each weekday; "Day N" labels are spread every other day from today."""
    if days[0] in WEEKDAYS:
        return [today + timedelta(days=(WEEKDAYS.index(d) - today.weekday()) % 7) for d in days]
    return [today + timedelta(days=i * FLEXIBLE_GAP_DAYS) for i in range(len(days))]


def parse_selection(raw: str, count: int, allowed: set[str]) -> list[LlmWorkout]:
    """Validates the LLM's exercise selection; exercises without a gif are dropped."""
    try:
        llm_plan = LlmPlan.model_validate_json(raw)
    except ValidationError as e:
        raise PlanGenerationError("LLM returned an invalid training plan") from e

    workouts = [
        w.model_copy(update={"exercises": [e for e in w.exercises if e.name in allowed]})
        for w in llm_plan.workouts[:count]
    ]
    if len(workouts) != count or not all(w.exercises for w in workouts):
        raise PlanGenerationError("LLM returned an incomplete training plan")
    return workouts


@lru_cache
def get_plan_agent() -> PlanAgent:
    return PlanAgent(get_llm())

import json
import logging
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import openai
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient, get_llm
from app.agents.plan import prompts
from app.agents.plan.descriptions import describe_exercises
from app.agents.plan.exercises import allowed_exercises, exercise_title, gif_url
from app.agents.plan.health import WINDOW_DAYS, health_summary
from app.core.config import settings
from app.models import PostWorkoutCheckIn, User, WorkoutFeedback
from app.rag.knowledge_base import KnowledgeBase
from app.schemas.feedback import FeedbackOut, PostWorkoutFeedback
from app.schemas.plan import PlanExercise, TrainingPlan, Workout
from app.schemas.post_workout import PostWorkoutFeedback as CheckInFeedback
from app.schemas.questionnaire import CamelModel, TrainingQuestionnaire
from app.services.post_workout import feedback_for

logger = logging.getLogger(__name__)

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

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.knowledge = KnowledgeBase("training")

    async def generate(
        self, db: Session, user: User, questionnaire: TrainingQuestionnaire, today: date | None = None
    ) -> TrainingPlan:
        health = health_summary(db, user)
        feedback = self.get_feedback(db, user.id, limit=FEEDBACK_LIMIT)
        check_ins = self.get_check_ins(db, user.id, limit=FEEDBACK_LIMIT)
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
            check_ins=json.dumps([c.model_dump(mode="json", by_alias=True) for c in check_ins], indent=2),
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
        self.save(user.id, plan)
        return plan

    def complete_workout(self, user_id: int, workout_date: date) -> tuple[TrainingPlan, Workout] | None:
        plan = self.get(user_id)
        workout = next((w for w in plan.workouts if w.date == workout_date), None) if plan else None
        if workout is None:
            return None
        plan.workouts.remove(workout)
        self.save(user_id, plan)
        return plan, workout

    async def regenerate_if_finished(
        self, db: Session, user: User, questionnaire: TrainingQuestionnaire | None
    ) -> TrainingPlan | None:
        plan = self.get(user.id)
        if questionnaire is None or plan is None or plan.workouts:
            return None
        try:
            return await self.generate(db, user, questionnaire, datetime.now(ZoneInfo(user.timezone)).date())
        except (openai.APIError, PlanGenerationError):
            logger.exception("Plan regeneration failed for user %s", user.id)
            return None

    def save_feedback(self, db: Session, user_id: int, feedback: PostWorkoutFeedback) -> FeedbackOut:
        row = WorkoutFeedback(user_id=user_id, **feedback.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return FeedbackOut.model_validate(row)

    def get_feedback(self, db: Session, user_id: int, limit: int) -> list[FeedbackOut]:
        rows = db.scalars(
            select(WorkoutFeedback)
            .where(WorkoutFeedback.user_id == user_id)
            .order_by(WorkoutFeedback.id.desc())
            .limit(limit)
        )
        return [FeedbackOut.model_validate(r) for r in rows]

    def get_check_ins(self, db: Session, user_id: int, limit: int) -> list[CheckInFeedback]:
        rows = db.scalars(
            select(PostWorkoutCheckIn)
            .where(PostWorkoutCheckIn.user_id == user_id, PostWorkoutCheckIn.status == "completed")
            .order_by(PostWorkoutCheckIn.workout_ended_at.desc())
            .limit(limit)
        )
        return [feedback_for(r, confirmed=True) for r in rows]

    def save(self, user_id: int, plan: TrainingPlan) -> None:
        self.plan_path(user_id).write_text(plan.model_dump_json(by_alias=True, indent=2), encoding="utf-8")

    def get(self, user_id: int) -> TrainingPlan | None:
        path = self.plan_path(user_id)
        if not path.exists():
            return None
        try:
            return TrainingPlan.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError:
            return None

    def plan_path(self, user_id: int) -> Path:
        path = Path(settings.training_plan_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{user_id}.json"


def plan_dates(days: list[str], today: date) -> list[date]:
    if days[0] in WEEKDAYS:
        return [today + timedelta(days=(WEEKDAYS.index(d) - today.weekday()) % 7) for d in days]
    return [today + timedelta(days=i * FLEXIBLE_GAP_DAYS) for i in range(len(days))]


def parse_selection(raw: str, count: int, allowed: set[str]) -> list[LlmWorkout]:
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

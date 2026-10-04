from datetime import date
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.plan.agent import PlanAgent, PlanGenerationError, get_plan_agent
from app.agents.training.agent import TrainingAgent, get_training_agent
from app.core.deps import CurrentUser, DbSession
from app.schemas.feedback import FeedbackIn, FeedbackOut
from app.schemas.plan import TrainingPlan, WorkoutDone
from app.schemas.post_workout import StartCheckIn
from app.services import post_workout as check_ins

router = APIRouter(prefix="/agents/plan", tags=["plan agent"])

Agent = Annotated[PlanAgent, Depends(get_plan_agent)]
Training = Annotated[TrainingAgent, Depends(get_training_agent)]


@router.post("", response_model=TrainingPlan)
async def generate_plan(user: CurrentUser, db: DbSession, agent: Agent, training: Training, today: date | None = None):
    """`today` is the user's local date (YYYY-MM-DD); the server date is used when it's missing."""
    questionnaire = training.get_status(db, user.id).training_questionnaire
    if questionnaire is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete the training questionnaire first")
    try:
        return await agent.generate(db, user, questionnaire, today)
    except PlanGenerationError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e


@router.get("", response_model=TrainingPlan)
def get_plan(user: CurrentUser, agent: Agent):
    plan = agent.get(user.id)
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No training plan yet")
    return plan


@router.post("/workouts/{workout_date}/done", response_model=WorkoutDone)
def complete_workout(workout_date: date, user: CurrentUser, db: DbSession, agent: Agent):
    """Removes the workout from the plan and starts a post-workout check-in for it."""
    done = agent.complete_workout(user.id, workout_date)
    if done is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No planned workout on this date")
    plan, workout = done
    start = StartCheckIn(
        request_id=uuid4(),
        workout_type=workout.focus[:80] or None,
        workout_duration_minutes=min(600, max(1, sum(e.estimated_time_minutes for e in workout.exercises))),
    )
    return WorkoutDone(plan=plan, check_in=check_ins.response_for(check_ins.create_checkin(db, user.id, start)))


@router.post("/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def add_feedback(data: FeedbackIn, user: CurrentUser, db: DbSession, agent: Agent):
    return agent.save_feedback(db, user.id, data.post_workout_feedback)


@router.get("/feedback", response_model=list[FeedbackOut])
def feedback_history(user: CurrentUser, db: DbSession, agent: Agent, limit: int = 50):
    return agent.get_feedback(db, user.id, limit=limit)

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.plan.agent import PlanAgent, PlanGenerationError, get_plan_agent
from app.agents.training.agent import TrainingAgent, get_training_agent
from app.core.deps import CurrentUser, DbSession
from app.schemas.feedback import FeedbackIn, FeedbackOut
from app.schemas.plan import TrainingPlan

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


@router.post("/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def add_feedback(data: FeedbackIn, user: CurrentUser, db: DbSession, agent: Agent):
    return agent.save_feedback(db, user.id, data.post_workout_feedback)


@router.get("/feedback", response_model=list[FeedbackOut])
def feedback_history(user: CurrentUser, db: DbSession, agent: Agent, limit: int = 50):
    return agent.get_feedback(db, user.id, limit=limit)

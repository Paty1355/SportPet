from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.agents.training.agent import TrainingAgent, get_training_agent
from app.core.deps import CurrentUser, DbSession
from app.schemas.questionnaire import QuestionnaireStatus

router = APIRouter(prefix="/agents/training/questionnaire", tags=["training questionnaire"])

Agent = Annotated[TrainingAgent, Depends(get_training_agent)]


@router.get("", response_model=QuestionnaireStatus)
def get_questionnaire(user: CurrentUser, db: DbSession, agent: Agent):
    return agent.get_status(db, user.id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def reset_questionnaire(user: CurrentUser, db: DbSession, agent: Agent):
    agent.reset(db, user.id)

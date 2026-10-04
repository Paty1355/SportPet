from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.agents.diet.agent import DietAgent, get_diet_agent
from app.core.deps import CurrentUser, DbSession
from app.schemas.questionnaire import DietQuestionnaireStatus

router = APIRouter(prefix="/agents/diet/questionnaire", tags=["diet questionnaire"])

Agent = Annotated[DietAgent, Depends(get_diet_agent)]


@router.get("", response_model=DietQuestionnaireStatus)
def get_questionnaire(user: CurrentUser, db: DbSession, agent: Agent):
    return agent.get_status(db, user.id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def reset_questionnaire(user: CurrentUser, db: DbSession, agent: Agent):
    agent.reset(db, user.id)

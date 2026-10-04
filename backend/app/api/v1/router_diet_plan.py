from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.diet.agent import DietAgent, get_diet_agent
from app.agents.diet_plan.agent import DietPlanAgent, DietPlanGenerationError, get_diet_plan_agent
from app.core.deps import CurrentUser, DbSession
from app.schemas.diet_plan import DietPlan

router = APIRouter(prefix="/agents/diet-plan", tags=["diet plan agent"])

Agent = Annotated[DietPlanAgent, Depends(get_diet_plan_agent)]
Diet = Annotated[DietAgent, Depends(get_diet_agent)]


@router.post("", response_model=DietPlan)
async def generate_plan(user: CurrentUser, db: DbSession, agent: Agent, diet: Diet):
    questionnaire = diet.get_status(db, user.id).diet_questionnaire
    if questionnaire is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete the diet questionnaire first")
    try:
        return await agent.generate(db, user, questionnaire)
    except DietPlanGenerationError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e


@router.get("", response_model=DietPlan)
def get_plan(user: CurrentUser, agent: Agent):
    plan = agent.get(user.id)
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No diet plan yet")
    return plan

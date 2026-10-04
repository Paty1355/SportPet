from typing import Annotated

from fastapi import APIRouter, Depends

from app.agents.diet.agent import DietAgent, get_diet_agent
from app.core.deps import CurrentUser, DbSession
from app.schemas.agent import AgentResponse, ChatRequest, MessageOut

router = APIRouter(prefix="/agents/diet", tags=["diet agent"])

Agent = Annotated[DietAgent, Depends(get_diet_agent)]


@router.post("/chat", response_model=AgentResponse)
async def chat(data: ChatRequest, user: CurrentUser, db: DbSession, agent: Agent):
    return await agent.run(db, user, data.message)


@router.get("/history", response_model=list[MessageOut])
def history(user: CurrentUser, db: DbSession, agent: Agent, limit: int = 50):
    return agent.get_history(db, user.id, limit=limit)

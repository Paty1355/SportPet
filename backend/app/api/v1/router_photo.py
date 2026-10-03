from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.agents.photo.agent import PhotoAgent, get_photo_agent
from app.core.deps import CurrentUser, DbSession
from app.schemas.agent import AgentResponse, MessageOut
from app.storage.files import save_image

router = APIRouter(prefix="/agents/photo", tags=["photo agent"])

Agent = Annotated[PhotoAgent, Depends(get_photo_agent)]


@router.post("", response_model=AgentResponse)
async def analyze_photo(
    user: CurrentUser,
    db: DbSession,
    agent: Agent,
    file: Annotated[UploadFile, File()],
    message: Annotated[str, Form(max_length=4000)] = "Opisz to zdjęcie.",
):
    _, image = await save_image(user.id, file)
    return await agent.run(db, user, message, image=image)


@router.get("/history", response_model=list[MessageOut])
def history(user: CurrentUser, db: DbSession, agent: Agent, limit: int = 50):
    return agent.get_history(db, user.id, limit=limit)

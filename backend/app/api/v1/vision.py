from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.agents.vision.agent import MachineNotRecognized, VisionAgent, VisionKnowledgeUnavailable, get_vision_agent
from app.agents.vision.llm import VisionModelResponseError
from app.schemas.vision import VisionResponse

router = APIRouter(prefix="/agents/vision", tags=["vision agent"])
Agent = Annotated[VisionAgent, Depends(get_vision_agent)]


@router.post("/analyze", response_model=VisionResponse)
async def analyze(file: Annotated[UploadFile, File()], agent: Agent):
    image = await file.read()
    if not image:
        raise HTTPException(422, "Provide a non-empty image")
    try:
        return await agent.run(image)
    except MachineNotRecognized as exc:
        raise HTTPException(422, str(exc)) from exc
    except VisionKnowledgeUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except VisionModelResponseError as exc:
        raise HTTPException(502, str(exc)) from exc

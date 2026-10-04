from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.agents.vision.agent import MachineNotRecognized, VisionAgent, VisionKnowledgeUnavailable, get_vision_agent
from app.agents.vision.images import ImagePreparationError, ImageTooLarge, prepare_image
from app.agents.vision.llm import VisionModelResponseError
from app.core.config import settings
from app.schemas.vision import VisionResponse

router = APIRouter(prefix="/agents/vision", tags=["vision agent"])
Agent = Annotated[VisionAgent, Depends(get_vision_agent)]


@router.post("/analyze", response_model=VisionResponse)
async def analyze(file: Annotated[UploadFile, File()], agent: Agent):
    limit = settings.max_upload_mb * 1024 * 1024
    image = await file.read(limit + 1)
    if len(image) > limit:
        raise HTTPException(413, f"Image exceeds the {settings.max_upload_mb} MB upload limit")
    try:
        prepared = await run_in_threadpool(prepare_image, image)
    except ImageTooLarge as exc:
        raise HTTPException(413, str(exc)) from exc
    except ImagePreparationError as exc:
        raise HTTPException(422, str(exc)) from exc
    try:
        return await agent.run(prepared)
    except MachineNotRecognized as exc:
        raise HTTPException(422, str(exc)) from exc
    except VisionKnowledgeUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except VisionModelResponseError as exc:
        raise HTTPException(502, str(exc)) from exc

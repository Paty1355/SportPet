from functools import lru_cache

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from app.agents.vision.knowledge import GymMachineKnowledge
from app.agents.vision.llm import AzureVisionLLM, VisionLLM
from app.core.azure import get_async_azure_client
from app.core.config import settings
from app.schemas.vision import VisionResponse


class VisionKnowledgeUnavailable(RuntimeError):
    pass


class MachineNotRecognized(ValueError):
    pass


class NotGymEquipment(MachineNotRecognized):
    pass


class VisionAgent:
    name = "vision"

    def __init__(self, llm: VisionLLM, knowledge: GymMachineKnowledge) -> None:
        self.llm = llm
        self.knowledge = knowledge

    async def run(self, image: bytes) -> VisionResponse:
        # Chroma and Azure embedding calls are synchronous: keep them off the event loop.
        catalog = await run_in_threadpool(self.knowledge.get_catalog)
        if not catalog:
            raise VisionKnowledgeUnavailable("Machine knowledge is empty; import machine cards first")
        identification = await self.llm.identify(image, catalog)
        if not identification.is_gym_equipment:
            raise NotGymEquipment(
                "This photo doesn't show gym equipment. Take a photo of the machine you want to use."
            )
        if identification.confidence != "high":
            # Instructions for the wrong machine are worse than asking for another photo.
            raise MachineNotRecognized(
                "I'm not sure which machine this is. Take a clearer photo of the whole machine."
            )
        selected = next((entry for entry in catalog if entry.machine_id == identification.machine_id), None)
        if selected is None:
            raise MachineNotRecognized("The image does not match a machine in the supported catalog")
        machine = await run_in_threadpool(self.knowledge.search, selected.name, selected.machine_id)
        if machine is None:
            raise VisionKnowledgeUnavailable("No knowledge card is available for the identified machine")
        usage = await self.llm.describe(machine)
        return VisionResponse(
            machine_id=machine.machine_id,
            machine_name=machine.name,
            category=machine.category,
            sources=machine.sources,
            **usage.model_dump(),
        )


@lru_cache
def get_vision_agent() -> VisionAgent:
    if not settings.azure_enabled:
        raise HTTPException(503, "Configure AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY to use VisionAgent")
    llm = AzureVisionLLM(
        get_async_azure_client(),
        vision_deployment=settings.azure_openai_vision_deployment or settings.azure_openai_chat_deployment,
        chat_deployment=settings.azure_openai_chat_deployment,
    )
    return VisionAgent(llm, GymMachineKnowledge())

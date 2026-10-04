import json
from typing import Protocol

from openai import AsyncAzureOpenAI, ContentFilterFinishReasonError, LengthFinishReasonError
from pydantic import BaseModel, ValidationError

from app.agents.base import GUARD
from app.agents.llm import to_data_url
from app.agents.vision.prompts import USAGE_SYSTEM_PROMPT, VISION_SYSTEM_PROMPT
from app.schemas.vision import MachineCatalogEntry, MachineDocument, MachineIdentification, MachineUsage


class VisionModelResponseError(RuntimeError):
    pass


class VisionLLM(Protocol):
    async def identify(self, image: bytes, catalog: list[MachineCatalogEntry]) -> MachineIdentification: ...

    async def describe(self, machine_context: MachineDocument) -> MachineUsage: ...


class AzureVisionLLM:
    def __init__(self, client: AsyncAzureOpenAI, vision_deployment: str, chat_deployment: str) -> None:
        self.client = client
        self.vision_deployment = vision_deployment
        self.chat_deployment = chat_deployment

    async def identify(self, image: bytes, catalog: list[MachineCatalogEntry]) -> MachineIdentification:
        return await self._parse(
            self.vision_deployment,
            [
                {"role": "system", "content": f"{VISION_SYSTEM_PROMPT}\n\n{GUARD}"},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Supported catalog:\n"
                            + json.dumps([entry.model_dump() for entry in catalog], ensure_ascii=False),
                        },
                        {"type": "image_url", "image_url": {"url": to_data_url(image)}},
                    ],
                },
            ],
            MachineIdentification,
        )

    async def describe(self, machine_context: MachineDocument) -> MachineUsage:
        return await self._parse(
            self.chat_deployment,
            [
                {"role": "system", "content": f"{USAGE_SYSTEM_PROMPT}\n\n{GUARD}"},
                {"role": "user", "content": machine_context.model_dump_json(indent=2)},
            ],
            MachineUsage,
        )

    async def _parse[T: BaseModel](self, deployment: str, messages: list[dict], schema: type[T]) -> T:
        try:
            completion = await self.client.beta.chat.completions.parse(
                model=deployment, messages=messages, response_format=schema
            )
        except (ValidationError, ContentFilterFinishReasonError, LengthFinishReasonError) as exc:
            raise VisionModelResponseError("Azure returned an invalid structured response") from exc
        if not completion.choices:
            raise VisionModelResponseError("Azure returned no response")
        message = completion.choices[0].message
        if message.refusal or message.parsed is None:
            raise VisionModelResponseError("Azure did not return the requested structured response")
        return message.parsed

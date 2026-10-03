import base64
from typing import Protocol

from openai import AsyncAzureOpenAI

from app.core.config import settings


class LLMClient(Protocol):
    async def complete(
        self, system: str, messages: list[dict], image: bytes | None = None, json_mode: bool = False
    ) -> str: ...


class StubLLM:
    """Atrapa używana, gdy Azure nie jest skonfigurowany (i w testach) – zwraca echo ostatniej wiadomości."""

    async def complete(
        self, system: str, messages: list[dict], image: bytes | None = None, json_mode: bool = False
    ) -> str:
        if json_mode:
            return "{}"
        suffix = " (+ zdjęcie)" if image else ""
        return f"[stub] {messages[-1]['content']}{suffix}"


class AzureLLM:
    """Azure OpenAI: tekst przez deployment czatu, a gdy jest zdjęcie – przez deployment vision."""

    def __init__(self, client: AsyncAzureOpenAI, chat_deployment: str, vision_deployment: str | None = None):
        self.client = client
        self.chat_deployment = chat_deployment
        self.vision_deployment = vision_deployment or chat_deployment

    async def complete(
        self, system: str, messages: list[dict], image: bytes | None = None, json_mode: bool = False
    ) -> str:
        payload = [{"role": "system", "content": system}, *messages]
        deployment = self.chat_deployment

        if image is not None:
            last = payload[-1]
            payload[-1] = {
                "role": last["role"],
                "content": [
                    {"type": "text", "text": last["content"]},
                    {"type": "image_url", "image_url": {"url": to_data_url(image)}},
                ],
            }
            deployment = self.vision_deployment

        extra = {"response_format": {"type": "json_object"}} if json_mode else {}
        response = await self.client.chat.completions.create(model=deployment, messages=payload, **extra)
        return response.choices[0].message.content or ""


def to_data_url(image: bytes) -> str:
    return f"data:{detect_image_type(image)};base64,{base64.b64encode(image).decode()}"


def detect_image_type(image: bytes) -> str:
    if image.startswith(b"\x89PNG"):
        return "image/png"
    if image[:4] == b"RIFF" and image[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def get_llm() -> LLMClient:
    if not settings.azure_enabled:
        return StubLLM()

    from app.core.azure import get_async_azure_client

    return AzureLLM(
        get_async_azure_client(),
        chat_deployment=settings.azure_openai_chat_deployment,
        vision_deployment=settings.azure_openai_vision_deployment,
    )

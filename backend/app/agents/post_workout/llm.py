import json
from typing import Protocol

from fastapi import HTTPException
from openai import ContentFilterFinishReasonError, LengthFinishReasonError
from pydantic import BaseModel, ValidationError

from app.agents.post_workout.prompts import EXTRACTION_PROMPT, SUPPORT_PROMPT
from app.core.azure import get_async_azure_client
from app.core.config import settings
from app.schemas.post_workout import AnswerExtraction, SupportText


class PostWorkoutModelError(RuntimeError):
    pass


class PostWorkoutLLM(Protocol):
    async def extract(self, context: dict) -> AnswerExtraction: ...
    async def support(self, context: dict) -> SupportText: ...


class AzurePostWorkoutLLM:
    async def extract(self, context: dict) -> AnswerExtraction:
        return await self._parse(EXTRACTION_PROMPT, context, AnswerExtraction)

    async def support(self, context: dict) -> SupportText:
        return await self._parse(SUPPORT_PROMPT, context, SupportText)

    async def _parse[T: BaseModel](self, prompt: str, context: dict, schema: type[T]) -> T:
        if not settings.azure_enabled:
            raise HTTPException(503, "Configure Azure OpenAI to use post-workout text analysis")
        client = get_async_azure_client().with_options(timeout=30.0, max_retries=1)
        try:
            completion = await client.beta.chat.completions.parse(
                model=settings.azure_openai_chat_deployment,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                ],
                response_format=schema,
            )
        except (ValidationError, ContentFilterFinishReasonError, LengthFinishReasonError) as exc:
            raise PostWorkoutModelError("Azure returned invalid post-workout structured output") from exc
        if not completion.choices:
            raise PostWorkoutModelError("Azure returned no post-workout response")
        message = completion.choices[0].message
        if message.refusal or message.parsed is None:
            raise PostWorkoutModelError("Azure did not return the required post-workout response")
        return message.parsed

from functools import lru_cache

from app.agents.base import BaseAgent
from app.agents.llm import get_llm
from app.agents.photo.prompts import SYSTEM_PROMPT


class PhotoAgent(BaseAgent):
    name = "photo"
    system_prompt = SYSTEM_PROMPT


@lru_cache
def get_photo_agent() -> PhotoAgent:
    return PhotoAgent(get_llm())

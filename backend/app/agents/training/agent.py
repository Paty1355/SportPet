from functools import lru_cache

from app.agents.base import BaseAgent
from app.agents.llm import get_llm
from app.agents.training.prompts import SYSTEM_PROMPT


class TrainingAgent(BaseAgent):
    name = "training"
    system_prompt = SYSTEM_PROMPT


@lru_cache
def get_training_agent() -> TrainingAgent:
    return TrainingAgent(get_llm())

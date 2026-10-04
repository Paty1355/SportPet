
from pydantic import BaseModel, ValidationError

from app.agents.llm import LLMClient
from app.agents.plan import prompts
from app.rag.knowledge_base import KnowledgeBase

RAG_K = 3


class LlmDescriptions(BaseModel):
    descriptions: dict[str, str]


async def describe_exercises(llm: LLMClient, knowledge: KnowledgeBase, names: list[str]) -> dict[str, str]:
    sections = []
    for name in names:
        fragments = [c.text for c in knowledge.search(f"{name} exercise technique", k=RAG_K)]
        sections.append(f"## {name}\n" + ("\n---\n".join(fragments) or "(no fragments found)"))

    messages = [{"role": "user", "content": "\n\n".join(sections)}]
    raw = await llm.complete(prompts.DESCRIPTION_PROMPT, messages, json_mode=True)
    try:
        return LlmDescriptions.model_validate_json(raw).descriptions
    except ValidationError:
        return {}

from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agents.diet_plan import prompts
from app.agents.diet_plan.images import allowed_dishes, image_url
from app.agents.llm import LLMClient, get_llm
from app.agents.plan.health import WINDOW_DAYS, health_summary
from app.core.config import settings
from app.models import User
from app.rag.knowledge_base import KnowledgeBase
from app.schemas.diet_plan import DietDay, DietPlan, Meal
from app.schemas.questionnaire import CamelModel, DietQuestionnaire

PLAN_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
RAG_K = 6


class DietPlanGenerationError(Exception):
    pass


class LlmDay(CamelModel):
    meals: list[Meal]


class LlmDietPlan(CamelModel):
    daily_calories: int
    days: list[LlmDay]


class DietPlanAgent:
    """Weekly meal plan: the LLM builds it from the questionnaire, recent health data and diet guidelines from RAG."""

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.knowledge = KnowledgeBase("diet")

    async def generate(self, db: Session, user: User, questionnaire: DietQuestionnaire) -> DietPlan:
        health = health_summary(db, user)
        dishes = allowed_dishes(questionnaire)
        if not dishes:
            raise DietPlanGenerationError("No dish in the catalogue fits the questionnaire")
        system = prompts.SYSTEM_PROMPT.format(
            count=len(PLAN_DAYS),
            days=", ".join(PLAN_DAYS),
            meals=questionnaire.meals_per_day,
            minutes=questionnaire.cooking_time_minutes,
            catalogue="\n".join(f"- {name}" for name in dishes),
        )
        user_message = prompts.USER_MESSAGE.format(
            questionnaire=questionnaire.model_dump_json(by_alias=True, indent=2),
            window=WINDOW_DAYS,
            health=health.model_dump_json(by_alias=True, indent=2),
            guidelines=self.guidelines(questionnaire),
        )
        raw = await self.llm.complete(system, [{"role": "user", "content": user_message}], json_mode=True)
        llm_plan = parse_plan(raw, questionnaire.meals_per_day, set(dishes))

        days = [
            DietDay(day=day, meals=[m.model_copy(update={"image_url": image_url(dishes[m.title])}) for m in d.meals])
            for day, d in zip(PLAN_DAYS, llm_plan.days, strict=True)
        ]
        plan = DietPlan(daily_calories=llm_plan.daily_calories, days=days, health_summary=health)
        self.plan_path(user.id).write_text(plan.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
        return plan

    def guidelines(self, questionnaire: DietQuestionnaire) -> str:
        q = questionnaire
        terms = [q.main_goal, q.diet_type, *q.medical_conditions, *q.allergies_and_intolerances]
        query = " ".join(terms).replace("_", " ") + " diet meal plan"
        chunks = self.knowledge.search(query, k=RAG_K)
        return "\n\n".join(f"[{c.source}]\n{c.text}" for c in chunks) or "(none)"

    def get(self, user_id: int) -> DietPlan | None:
        path = self.plan_path(user_id)
        if not path.exists():
            return None
        try:
            return DietPlan.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError:
            return None  # saved in an older format; the user has to generate a new plan

    def plan_path(self, user_id: int) -> Path:
        path = Path(settings.diet_plan_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{user_id}.json"


def parse_plan(raw: str, meals_per_day: int, dishes: set[str]) -> LlmDietPlan:
    """Validates the LLM plan: one day per plan day, the requested meals per day, every dish from the catalogue."""
    try:
        llm_plan = LlmDietPlan.model_validate_json(raw)
    except ValidationError as e:
        raise DietPlanGenerationError("LLM returned an invalid diet plan") from e

    days = llm_plan.days[: len(PLAN_DAYS)]
    if len(days) != len(PLAN_DAYS) or any(len(d.meals) != meals_per_day for d in days):
        raise DietPlanGenerationError("LLM returned an incomplete diet plan")
    if any(m.title not in dishes for d in days for m in d.meals):
        raise DietPlanGenerationError("LLM returned a dish that is not in the catalogue")
    return llm_plan.model_copy(update={"days": days})


@lru_cache
def get_diet_plan_agent() -> DietPlanAgent:
    return DietPlanAgent(get_llm())

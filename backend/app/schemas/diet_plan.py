from app.schemas.plan import HealthSummary
from app.schemas.questionnaire import CamelModel


class Meal(CamelModel):
    name: str  # e.g. "Breakfast"
    title: str
    description: str  # ingredients with amounts and a short preparation
    calories: int
    protein_grams: int
    carbs_grams: int
    fat_grams: int
    prep_time_minutes: int
    image_url: str = ""  # decorative, set by the backend (not by the LLM)


class DietDay(CamelModel):
    day: str
    meals: list[Meal]


class DietPlan(CamelModel):
    daily_calories: int
    days: list[DietDay]
    health_summary: HealthSummary | None = None

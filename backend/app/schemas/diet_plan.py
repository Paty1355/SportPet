from app.schemas.plan import HealthSummary
from app.schemas.questionnaire import CamelModel


class Meal(CamelModel):
    name: str
    title: str
    description: str
    calories: int
    protein_grams: int
    carbs_grams: int
    fat_grams: int
    prep_time_minutes: int
    image_url: str = ""


class DietDay(CamelModel):
    day: str
    meals: list[Meal]


class DietPlan(CamelModel):
    daily_calories: int
    days: list[DietDay]
    health_summary: HealthSummary | None = None

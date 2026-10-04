import asyncio
import json
from typing import get_args, get_origin

from pydantic.alias_generators import to_camel

from app.agents.diet.agent import DietAgent
from app.agents.diet.questionnaire import NONE, QUESTIONS
from app.agents.diet_plan.agent import PLAN_DAYS, DietPlanAgent, LlmDietPlan, check_plan, get_diet_plan_agent
from app.agents.diet_plan.images import CONTAINS, allowed_dishes, available_dishes
from app.db.session import get_db
from app.main import app
from app.models import User
from app.schemas.questionnaire import DietQuestionnaire
from app.schemas.rag import Chunk

URL = "/api/v1/agents/diet/questionnaire"
CHAT_URL = "/api/v1/agents/diet/chat"
PLAN_URL = "/api/v1/agents/diet-plan"
ANSWERS = [
    "2", "vegan", "gluten, nuts", "1,4", "4", "30", "moderate", "about 2,400 kcal", "diabetes", "late_night_snacking",
    "gradual",
]  # fmt: skip


def complete(client, headers):
    for answer in ANSWERS:
        res = client.post(CHAT_URL, json={"message": answer}, headers=headers)
        assert res.status_code == 200, res.text
    return res


def test_full_questionnaire_produces_json(client, auth_headers):
    assert complete(client, auth_headers).json()["question"] is None

    status = client.get(URL, headers=auth_headers).json()
    assert status["completed"] is True
    assert status["dietQuestionnaire"] == {
        "mainGoal": "muscle_gain",
        "dietType": "vegan",
        "allergiesAndIntolerances": ["gluten", "nuts"],
        "dislikedFoods": ["fish", "vegetables"],
        "mealsPerDay": 4,
        "cookingTimeMinutes": 30,
        "activityLevel": "moderate",
        "calorieTarget": 2400,
        "medicalConditions": ["diabetes"],
        "eatingHabits": ["late_night_snacking"],
        "gentleCheck": {"gradualStart": True, "notes": ""},
        "healthNotes": "",
    }


def test_none_option_gives_empty_list_and_unclear_answer_repeats(client, auth_headers):
    res = client.post(CHAT_URL, json={"message": "banana"}, headers=auth_headers).json()
    assert res["question"]["key"] == "mainGoal"
    for answer in ["1", "1", "none", "none", "3", "15", "light", "auto", "none", "none", "standard"]:
        client.post(CHAT_URL, json={"message": answer}, headers=auth_headers)

    result = client.get(URL, headers=auth_headers).json()["dietQuestionnaire"]
    assert result["allergiesAndIntolerances"] == [] and result["medicalConditions"] == []
    assert result["calorieTarget"] is None
    assert result["gentleCheck"]["gradualStart"] is False


def test_too_low_calorie_target_warns_and_is_raised_to_minimum(client, auth_headers):
    for answer in ["1", "1", "none", "none", "3", "15", "light"]:
        client.post(CHAT_URL, json={"message": answer}, headers=auth_headers)

    res = client.post(CHAT_URL, json={"message": "800 kcal"}, headers=auth_headers).json()
    assert "below a healthy minimum" in res["reply"] and res["question"]["key"] == "medicalConditions"

    for answer in ["none", "none", "standard"]:
        client.post(CHAT_URL, json={"message": answer}, headers=auth_headers)
    result = client.get(URL, headers=auth_headers).json()["dietQuestionnaire"]
    assert result["calorieTarget"] == 1500  # the test user has no sex set, so the higher minimum applies


def test_gentle_question_recaps_and_recommends_gradual_start_for_medical_condition(client, auth_headers):
    for answer in ["1", "1", "none", "none", "3", "15", "light", "auto", "hypertension", "none"]:
        res = client.post(CHAT_URL, json={"message": answer}, headers=auth_headers).json()

    assert res["question"]["key"] == "gentleCheck"
    assert "High blood pressure" in res["reply"] and "gradual start" in res["reply"]


def test_diet_and_gym_questionnaires_are_independent(client, auth_headers):
    complete(client, auth_headers)
    gym = client.get("/api/v1/agents/training/questionnaire", headers=auth_headers).json()
    assert gym["step"] == 0 and gym["completed"] is False

    assert client.delete(URL, headers=auth_headers).status_code == 204
    assert client.get(URL, headers=auth_headers).json()["step"] == 0


def test_chat_injects_retrieved_chunks_into_system_prompt(client, auth_headers):
    complete(client, auth_headers)

    class CapturingLLM:
        async def complete(self, system, messages, image=None, json_mode=False):
            self.system, self.messages = system, messages
            return "ok"

    llm = CapturingLLM()
    agent = DietAgent(llm)
    agent.knowledge_base.add_chunks([Chunk(text="Protein needs", source="nutrition.pdf", page=3, chunk_index=0)])
    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).one()
    asyncio.run(agent.run(db, user, "Protein needs"))

    assert "[nutrition.pdf, p. 3]\nProtein needs" in llm.system
    assert '"dietType": "vegan"' in llm.messages[0]["content"]
    assert "dietType" not in llm.system


def test_schema_literals_match_question_options():
    fields = {to_camel(name): field.annotation for name, field in DietQuestionnaire.model_fields.items()}

    for question in QUESTIONS:
        if question.key in ("gentleCheck", "calorieTarget"):  # an object / a number, not a literal
            continue
        annotation = fields[question.key]
        if get_origin(annotation) is list:
            annotation = get_args(annotation)[0]
        assert {str(v) for v in get_args(annotation)} == set(question.options) - {NONE}, question.key


class PlanLLM:
    """Returns a 7-day plan with `meals` meals per day."""

    def __init__(self, meals: int, title: str = "Fruit with chickpeas"):
        meal = {"name": "Lunch", "title": title, "description": "...", "calories": 600}
        meal |= {"proteinGrams": 30, "carbsGrams": 60, "fatGrams": 20, "prepTimeMinutes": 20}
        self.plan = json.dumps({"dailyCalories": 2400, "days": [{"meals": [meal] * meals}] * 7})

    async def complete(self, system, messages, image=None, json_mode=False):
        return self.plan


def test_diet_plan_needs_questionnaire_and_valid_llm_output(client, auth_headers):
    assert client.post(PLAN_URL, headers=auth_headers).status_code == 409
    assert client.get(PLAN_URL, headers=auth_headers).status_code == 404
    complete(client, auth_headers)
    assert client.post(PLAN_URL, headers=auth_headers).status_code == 502  # stub LLM returns "{}"

    app.dependency_overrides[get_diet_plan_agent] = lambda: DietPlanAgent(PlanLLM(meals=3))
    assert client.post(PLAN_URL, headers=auth_headers).status_code == 502  # questionnaire asks for 4 meals

    app.dependency_overrides[get_diet_plan_agent] = lambda: DietPlanAgent(PlanLLM(meals=4))
    plan = client.post(PLAN_URL, headers=auth_headers).json()
    assert [d["day"] for d in plan["days"]][::6] == ["Monday", "Sunday"]
    assert plan["dailyCalories"] == 2400 and all(len(d["meals"]) == 4 for d in plan["days"])
    assert client.get(PLAN_URL, headers=auth_headers).json() == plan
    assert {m["imageUrl"] for d in plan["days"] for m in d["meals"]} == {"/static/meals/Fruit%20with%20chickpeas.jpg"}
    assert client.get("/static/meals/Fruit%20with%20chickpeas.jpg").headers["content-type"] == "image/jpeg"


def test_every_dish_photo_is_tagged():
    assert set(available_dishes()) == set(CONTAINS)  # an untagged photo would be hidden from users with restrictions


def questionnaire(**changes) -> DietQuestionnaire:
    base = {"main_goal": "maintenance", "diet_type": "omnivore", "allergies_and_intolerances": [], "disliked_foods": []}
    base |= {"meals_per_day": 3, "cooking_time_minutes": 30, "activity_level": "light", "medical_conditions": []}
    base |= {"eating_habits": [], "gentle_check": {"gradual_start": False, "notes": ""}}
    return DietQuestionnaire(**(base | changes))


def test_dish_catalogue_respects_diet_allergies_and_dislikes():
    assert set(allowed_dishes(questionnaire())) == set(available_dishes())
    vegan = allowed_dishes(questionnaire(diet_type="vegan", allergies_and_intolerances=["gluten", "nuts"]))
    assert "Fruit with chickpeas" in vegan and "Exotic smoothie with kale" in vegan
    assert all(not CONTAINS[d] & {"meat", "fish", "egg", "dairy", "gluten", "nuts"} for d in vegan)
    pesc = allowed_dishes(
        questionnaire(diet_type="pescatarian", allergies_and_intolerances=["lactose"], disliked_foods=["fish"])
    )
    assert pesc and all(not CONTAINS[d] & {"meat", "fish", "dairy"} for d in pesc)


def test_plan_with_dish_outside_the_catalogue_is_rejected(client, auth_headers):
    complete(client, auth_headers)  # vegan, no gluten/nuts, dislikes fish and vegetables
    app.dependency_overrides[get_diet_plan_agent] = lambda: DietPlanAgent(PlanLLM(meals=4, title="Chicken skewers"))
    assert client.post(PLAN_URL, headers=auth_headers).status_code == 502


def make_plan(description: str, calories: int = 2000) -> LlmDietPlan:
    meal = {"name": "Lunch", "title": "Fruit with chickpeas", "description": description, "calories": calories}
    meal |= {"proteinGrams": 30, "carbsGrams": 60, "fatGrams": 20, "prepTimeMinutes": 20}
    return LlmDietPlan.model_validate({"dailyCalories": calories, "days": [{"meals": [meal]}] * 7})


def test_check_plan_flags_allergens_diet_type_and_low_calories():
    vegan = questionnaire(diet_type="vegan", allergies_and_intolerances=["nuts"])

    assert check_plan(make_plan("fruit and chickpeas with almond milk"), vegan, "F") == [
        f'{day}, "Fruit with chickpeas": contains nuts' for day in PLAN_DAYS
    ]
    assert "contains lactose" in check_plan(make_plan("fruit with parmesan"), vegan, "F")[0]
    assert "contains meat" in check_plan(make_plan("chickpeas with chicken"), vegan, "F")[0]
    assert check_plan(make_plan("fruit with coconut yogurt and egg-free granola"), vegan, "F") == []
    assert check_plan(make_plan("fruit", calories=1300), vegan, "M") == ["dailyCalories must be at least 1500"]

    with_target = vegan.model_copy(update={"calorie_target": 1800})
    assert check_plan(make_plan("fruit", calories=1900), with_target, "F") == []
    assert check_plan(make_plan("fruit", calories=2400), with_target, "F") == [
        "dailyCalories must be about 1800, the user's calorie target"
    ]

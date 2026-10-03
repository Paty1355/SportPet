import asyncio
from typing import get_args, get_origin

from pydantic.alias_generators import to_camel

from app.agents.diet.agent import DietAgent
from app.agents.diet.questionnaire import NONE, QUESTIONS
from app.db.session import get_db
from app.main import app
from app.models import User
from app.schemas.questionnaire import DietQuestionnaire
from app.schemas.rag import Chunk

URL = "/api/v1/agents/diet/questionnaire"
CHAT_URL = "/api/v1/agents/diet/chat"
ANSWERS = ["2", "vegan", "gluten, nuts", "1,4", "4", "30", "moderate", "diabetes", "late_night_snacking", "gradual"]


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
        "medicalConditions": ["diabetes"],
        "eatingHabits": ["late_night_snacking"],
        "gentleCheck": {"gradualStart": True, "notes": ""},
    }


def test_none_option_gives_empty_list_and_unclear_answer_repeats(client, auth_headers):
    res = client.post(CHAT_URL, json={"message": "banana"}, headers=auth_headers).json()
    assert res["question"]["key"] == "mainGoal"
    for answer in ["1", "1", "none", "none", "3", "15", "light", "none", "none", "standard"]:
        client.post(CHAT_URL, json={"message": answer}, headers=auth_headers)

    result = client.get(URL, headers=auth_headers).json()["dietQuestionnaire"]
    assert result["allergiesAndIntolerances"] == [] and result["medicalConditions"] == []
    assert result["gentleCheck"]["gradualStart"] is False


def test_gentle_question_recaps_and_recommends_gradual_start_for_medical_condition(client, auth_headers):
    for answer in ["1", "1", "none", "none", "3", "15", "light", "hypertension", "none"]:
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
            self.system = system
            return "ok"

    llm = CapturingLLM()
    agent = DietAgent(llm)
    agent.knowledge_base.add_chunks([Chunk(text="Protein needs", source="nutrition.pdf", page=3, chunk_index=0)])
    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).one()
    asyncio.run(agent.run(db, user, "Protein needs"))

    assert "[nutrition.pdf, p. 3]\nProtein needs" in llm.system
    assert "Diet questionnaire:" in llm.system


def test_schema_literals_match_question_options():
    fields = {to_camel(name): field.annotation for name, field in DietQuestionnaire.model_fields.items()}

    for question in QUESTIONS:
        if question.key == "gentleCheck":
            continue
        annotation = fields[question.key]
        if get_origin(annotation) is list:
            annotation = get_args(annotation)[0]
        assert {str(v) for v in get_args(annotation)} == set(question.options) - {NONE}, question.key

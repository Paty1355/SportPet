from typing import get_args, get_origin

from pydantic.alias_generators import to_camel

from app.agents.training.questionnaire import NONE, QUESTIONS
from app.schemas.questionnaire import TrainingQuestionnaire

URL = "/api/v1/agents/training/questionnaire"
CHAT_URL = "/api/v1/agents/training/chat"


def test_status_before_first_answer_shows_first_question(client, auth_headers):
    status = client.get(URL, headers=auth_headers).json()
    assert status["step"] == 0
    assert status["completed"] is False
    assert status["question"]["key"] == "mainGoal"
    assert status["trainingQuestionnaire"] is None


def test_first_message_answers_first_question(client, auth_headers):
    res = client.post(CHAT_URL, json={"message": "postpartum"}, headers=auth_headers).json()
    assert res["question"]["key"] == "experienceLevel"
    assert client.get(URL, headers=auth_headers).json()["step"] == 1


def test_full_questionnaire_produces_json(client, auth_headers, complete_questionnaire):
    res = complete_questionnaire(auth_headers).json()
    assert res["question"] is None

    status = client.get(URL, headers=auth_headers).json()
    assert status["completed"] is True
    assert status["trainingQuestionnaire"] == {
        "mainGoal": "postpartum",
        "experienceLevel": "returning",
        "priorityBodyParts": ["glutes", "core"],
        "likedExercises": ["weights", "machines"],
        "dislikedExercises": ["burpees", "jumping"],
        "injuriesAndLimitations": ["back", "diastasis"],
        "preferredDays": "mwf",
        "trainingDaysPerWeek": 3,
        "workoutDurationMinutes": 60,
        "lifestyleAndStress": "active",
        "intensityCheck": {"cautiousStart": True, "notes": ""},
        "healthNotes": "",
    }


def test_unclear_answer_repeats_question(client, auth_headers):
    res = client.post(CHAT_URL, json={"message": "banana"}, headers=auth_headers).json()
    assert "didn't quite get that" in res["reply"]
    assert res["question"]["key"] == "mainGoal"

    res = client.post(CHAT_URL, json={"message": "1, 2"}, headers=auth_headers).json()
    assert res["question"]["key"] == "mainGoal"


def test_none_option_gives_empty_list(client, auth_headers):
    answers = ["1", "1", "1", "1", "none", "I'm fully healthy", "weekends", "40", "balanced", "standard"]
    for answer in answers:
        client.post(CHAT_URL, json={"message": answer}, headers=auth_headers)

    result = client.get(URL, headers=auth_headers).json()["trainingQuestionnaire"]
    assert result["dislikedExercises"] == []
    assert result["injuriesAndLimitations"] == []
    assert result["trainingDaysPerWeek"] == 2
    assert result["intensityCheck"]["cautiousStart"] is False


def test_intensity_question_recaps_and_recommends_caution(client, auth_headers):
    for answer in ["postpartum", "1", "1", "1", "1", "1", "1", "1", "1"]:
        res = client.post(CHAT_URL, json={"message": answer}, headers=auth_headers).json()

    assert res["question"]["key"] == "intensityCheck"
    assert "Getting back in shape after pregnancy" in res["reply"]
    assert "cautious start" in res["reply"]


def test_reset(client, auth_headers, complete_questionnaire):
    complete_questionnaire(auth_headers)
    assert client.delete(URL, headers=auth_headers).status_code == 204

    status = client.get(URL, headers=auth_headers).json()
    assert status["completed"] is False
    assert status["step"] == 0


def test_schema_literals_match_question_options():
    fields = {to_camel(name): field.annotation for name, field in TrainingQuestionnaire.model_fields.items()}

    for question in QUESTIONS:
        if question.key == "intensityCheck":
            continue
        annotation = fields[question.key]
        if get_origin(annotation) is list:
            annotation = get_args(annotation)[0]
        assert {str(v) for v in get_args(annotation)} == set(question.options) - {NONE}, question.key

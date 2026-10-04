import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from openai import AsyncAzureOpenAI
from sqlalchemy import func, select

from app.agents.post_workout.agent import PostWorkoutAgent, get_post_workout_agent
from app.agents.post_workout.llm import AzurePostWorkoutLLM, PostWorkoutModelError
from app.agents.post_workout.safety import literal_observations
from app.db.session import get_db
from app.main import app
from app.models import Message, PostWorkoutCheckIn, PostWorkoutReport
from app.schemas.post_workout import AnswerExtraction, SafetyObservation, SupportText


class ControlledLLM:
    def __init__(self):
        self.extract_calls = []
        self.support_calls = []
        self.fail_support = False
        self.extraction = None

    async def extract(self, context):
        self.extract_calls.append(context)
        if self.extraction is not None:
            return self.extraction
        key = context["question"]["key"]
        return AnswerExtraction(
            score=7 if key == "fatigueLevel" and "seven" in context["message"] else None,
            choice=None,
            locations=["knee"] if key == "painLocations" else [],
            text="Knee pain while bending." if key == "painLocations" else None,
            needs_clarification=key not in {"painLocations", "fatigueLevel"},
            safety_observations=[],
        )

    async def support(self, context):
        self.support_calls.append(context)
        if self.fail_support:
            raise PostWorkoutModelError("test provider failure")
        return SupportText(message="Thanks for checking in and noticing how you feel.", observation_ids=[])


@pytest.fixture
def post_client(client):
    llm = ControlledLLM()
    app.dependency_overrides[get_post_workout_agent] = lambda: PostWorkoutAgent(llm)
    return client, llm


def start(client, headers, **extra):
    response = client.post(
        "/api/v1/agents/post-workout/sessions", json={"requestId": str(uuid4()), **extra}, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def turn(client, headers, session, *, action="answer", message=None, **extra):
    payload = {"requestId": str(uuid4()), "expectedVersion": session["version"], "action": action, **extra}
    if message is not None:
        payload["message"] = message
    response = client.post(
        f"/api/v1/agents/post-workout/sessions/{session['sessionId']}/chat", json=payload, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def complete(client, headers, **extra):
    session = start(client, headers, **extra)
    for answer in ("no", "4", "better", "7", "8", "7"):
        session = turn(client, headers, session, message=answer)
    assert session["status"] == "awaiting_confirmation"
    return turn(client, headers, session, action="confirm")


def test_complete_uses_shared_messages_and_saves_report(post_client, auth_headers):
    client, llm = post_client
    session = complete(client, auth_headers)
    assert session["status"] == "completed"
    assert session["postWorkoutFeedback"]["fatigueLevel"] == 4
    assert session["postWorkoutFeedback"]["pain"] == {
        "experienced": False,
        "intensity": 0,
        "locations": [],
        "description": None,
    }
    assert session["support"]["status"] == "available"
    assert len(llm.support_calls) == 1
    assert not llm.extract_calls
    report = client.get("/api/v1/agents/post-workout/reports", headers=auth_headers).json()[0]
    assert report["id"] == session["reportId"]
    assert report["statistics"]["sampleCount"] == 1
    assert report["statistics"]["status"] == "insufficient_data"
    history = client.get(
        f"/api/v1/agents/post-workout/sessions/{session['sessionId']}/history", headers=auth_headers
    ).json()
    assert len(history) == 15  # initial question + six answers + confirmation, each with its reply
    assert history[-1]["content"] == session["reply"]
    db = next(app.dependency_overrides[get_db]())
    assert db.scalar(select(func.count()).select_from(PostWorkoutCheckIn)) == 1
    assert db.scalar(select(func.count()).select_from(PostWorkoutReport)) == 1
    assert set(db.scalars(select(Message.agent))) == {"post_workout"}


def test_preferences_use_existing_me_endpoint(post_client, auth_headers):
    client, _ = post_client
    response = client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={"post_workout_reporting_frequency": "monthly", "timezone": "UTC"},
    )
    assert response.status_code == 200
    assert response.json()["post_workout_reporting_frequency"] == "monthly"
    assert response.json()["timezone"] == "UTC"
    complete(client, auth_headers)
    report = client.get("/api/v1/agents/post-workout/reports", headers=auth_headers).json()[0]
    assert report["period"] == "monthly"
    assert report["timezone"] == "UTC"
    for payload in (
        {"timezone": "Unknown/Zone"},
        {"timezone": None},
        {"post_workout_reporting_frequency": None},
        {"post_workout_reporting_frequency": "yearly"},
    ):
        assert client.patch("/api/v1/users/me", headers=auth_headers, json=payload).status_code == 422


def test_user_cannot_access_another_users_sessions_or_reports(post_client, auth_headers):
    client, _ = post_client
    owned = complete(client, auth_headers)
    client.post("/api/v1/auth/register", json={"email": "other@example.com", "password": "password123"})
    token = client.post("/api/v1/auth/login", data={"username": "other@example.com", "password": "password123"}).json()
    other = {"Authorization": f"Bearer {token['access_token']}"}
    path = f"/api/v1/agents/post-workout/sessions/{owned['sessionId']}"
    assert client.get(path, headers=other).status_code == 404
    assert client.get(path + "/history", headers=other).status_code == 404
    assert (
        client.post(
            path + "/chat",
            headers=other,
            json={
                "requestId": str(uuid4()),
                "expectedVersion": owned["version"],
                "action": "confirm",
            },
        ).status_code
        == 404
    )
    assert client.get("/api/v1/agents/post-workout/feedback", headers=other).json() == []
    assert client.get("/api/v1/agents/post-workout/reports", headers=other).json() == []


def test_start_and_turn_retries_are_idempotent(post_client, auth_headers):
    client, _ = post_client
    payload = {"requestId": str(uuid4())}
    url = "/api/v1/agents/post-workout/sessions"
    first = client.post(url, headers=auth_headers, json=payload).json()
    assert client.post(url, headers=auth_headers, json=payload).json()["sessionId"] == first["sessionId"]
    assert client.post(url, headers=auth_headers, json={**payload, "workoutType": "cardio"}).status_code == 409
    chat = f"{url}/{first['sessionId']}/chat"
    answer = {"requestId": str(uuid4()), "expectedVersion": first["version"], "message": "no"}
    result = client.post(chat, headers=auth_headers, json=answer)
    assert result.status_code == 200
    assert client.post(chat, headers=auth_headers, json=answer).json() == result.json()
    assert client.post(chat, headers=auth_headers, json={**answer, "message": "yes"}).status_code == 409
    assert client.post(chat, headers=auth_headers, json={**answer, "requestId": str(uuid4())}).status_code == 409


def test_confirmation_retry_does_not_generate_again(post_client, auth_headers):
    client, llm = post_client
    session = start(client, auth_headers)
    for answer in ("no", "4", "same", "6", "7", "5"):
        session = turn(client, auth_headers, session, message=answer)
    payload = {"requestId": str(uuid4()), "expectedVersion": session["version"], "action": "confirm"}
    url = f"/api/v1/agents/post-workout/sessions/{session['sessionId']}/chat"
    first = client.post(url, headers=auth_headers, json=payload)
    assert first.status_code == 200
    assert client.post(url, headers=auth_headers, json=payload).json() == first.json()
    assert len(llm.support_calls) == 1


def test_pain_followups_and_correction(post_client, auth_headers):
    client, llm = post_client
    session = start(client, auth_headers)
    session = turn(client, auth_headers, session, message="yes")
    assert session["question"]["key"] == "painLocations"
    session = turn(client, auth_headers, session, message="My knee hurts when I bend it")
    assert session["draftFeedback"]["pain"]["locations"] == ["knee"]
    session = turn(client, auth_headers, session, message="8")
    assert session["notice"]["level"] == "consultation"
    session = turn(client, auth_headers, session, action="correct", fieldKey="painExperienced", message="no")
    assert session["draftFeedback"]["pain"]["intensity"] == 0
    assert session["draftFeedback"]["pain"]["locations"] == []
    assert session["draftFeedback"]["pain"]["description"] is None
    assert session["total"] == 6
    assert len(llm.extract_calls) == 1


def test_skipped_scores_remain_null_and_zero_is_a_real_score(post_client, auth_headers):
    client, _ = post_client
    session = start(client, auth_headers)
    session = turn(client, auth_headers, session, action="skip")
    session = turn(client, auth_headers, session, message="0")
    for _ in range(4):
        session = turn(client, auth_headers, session, action="skip")
    final = turn(client, auth_headers, session, action="confirm")
    feedback = final["postWorkoutFeedback"]
    assert feedback["fatigueLevel"] == 0
    assert feedback["motivationLevel"] is None
    assert feedback["pain"]["experienced"] is None
    report = client.get("/api/v1/agents/post-workout/reports", headers=auth_headers).json()[0]
    assert report["statistics"]["metrics"]["fatigueLevel"]["median"] == 0
    assert report["statistics"]["metrics"]["motivationLevel"]["count"] == 0


def test_ambiguous_or_out_of_range_score_does_not_advance(post_client, auth_headers):
    client, llm = post_client
    session = turn(client, auth_headers, start(client, auth_headers), message="no")
    session = turn(client, auth_headers, session, message="11")
    assert session["question"]["key"] == "fatigueLevel"
    assert not llm.extract_calls
    llm.extraction = AnswerExtraction(
        score=None, choice=None, locations=[], text=None, needs_clarification=True, safety_observations=[]
    )
    session = turn(client, auth_headers, session, message="Very tired")
    assert session["question"]["key"] == "fatigueLevel"
    assert session["draftFeedback"]["fatigueLevel"] is None


def test_free_text_score_and_profile_context(post_client, auth_headers, complete_questionnaire):
    client, llm = post_client
    complete_questionnaire(auth_headers)
    session = turn(client, auth_headers, start(client, auth_headers), message="no")
    session = turn(client, auth_headers, session, message="I would say seven")
    assert session["draftFeedback"]["fatigueLevel"] == 7
    for answer in ("better", "7", "8", "6"):
        session = turn(client, auth_headers, session, message=answer)
    turn(client, auth_headers, session, action="confirm")
    assert llm.support_calls[0]["profile"]["training_questionnaire"]["mainGoal"] == ["postpartum"]
    assert "email" not in llm.support_calls[0]["profile"]


@pytest.mark.parametrize(
    "message", ["I have chest pain", "I can't breathe", "I want to hurt myself", "Boli mnie w klatce"]
)
def test_urgent_statement_at_any_step_interrupts_without_llm(post_client, auth_headers, message):
    client, llm = post_client
    session = turn(client, auth_headers, start(client, auth_headers), message="no")
    session = turn(client, auth_headers, session, message=message)
    assert session["status"] == "interrupted"
    assert session["notice"]["level"] == "urgent"
    assert session["question"] is None
    assert session["postWorkoutFeedback"] is None
    assert not llm.extract_calls and not llm.support_calls
    assert client.get("/api/v1/agents/post-workout/feedback", headers=auth_headers).json() == []


@pytest.mark.parametrize(
    "message",
    [
        "I have no chest pain",
        "I don't have chest pain",
        "If I have chest pain?",
        "My friend has chest pain",
        "I had chest pain yesterday",
    ],
)
def test_literal_checks_do_not_flag_negated_hypothetical_or_third_person(message):
    assert literal_observations(message) == []


def test_verified_provider_safety_observation_is_applied(post_client, auth_headers):
    client, llm = post_client
    session = turn(client, auth_headers, start(client, auth_headers), message="no")
    llm.extraction = AnswerExtraction(
        score=None,
        choice=None,
        locations=[],
        text=None,
        needs_clarification=True,
        safety_observations=[
            SafetyObservation(code="persistent_distress", evidence="I have struggled to cope for weeks")
        ],
    )
    session = turn(client, auth_headers, session, message="I have struggled to cope for weeks")
    assert session["notice"]["level"] == "consultation"
    assert "psychologist" in session["notice"]["message"]
    assert session["question"]["key"] == "fatigueLevel"


def test_fabricated_safety_evidence_is_not_applied(post_client, auth_headers):
    client, llm = post_client
    session = turn(client, auth_headers, start(client, auth_headers), message="no")
    llm.extraction = AnswerExtraction(
        score=None,
        choice=None,
        locations=[],
        text=None,
        needs_clarification=True,
        safety_observations=[SafetyObservation(code="self_harm_risk", evidence="fabricated")],
    )
    session = turn(client, auth_headers, session, message="I am tired")
    assert session["status"] == "in_progress"
    assert session["notice"] is None


def test_model_failure_preserves_feedback_and_can_retry_support(post_client, auth_headers):
    client, llm = post_client
    llm.fail_support = True
    session = complete(client, auth_headers)
    assert session["status"] == "completed"
    assert session["support"]["status"] == "unavailable"
    assert len(client.get("/api/v1/agents/post-workout/feedback", headers=auth_headers).json()) == 1
    llm.fail_support = False
    retry = turn(client, auth_headers, session, action="retry_support")
    assert retry["support"]["status"] == "available"
    report = client.get("/api/v1/agents/post-workout/reports", headers=auth_headers).json()[0]
    assert report["support"]["status"] == "available"
    assert len(client.get("/api/v1/agents/post-workout/feedback", headers=auth_headers).json()) == 1


def test_completed_feedback_is_committed_before_model_call(post_client, auth_headers):
    client, llm = post_client
    original = llm.support

    async def observe_commit(context):
        db = next(app.dependency_overrides[get_db]())
        assert (
            db.scalar(
                select(func.count()).select_from(PostWorkoutCheckIn).where(PostWorkoutCheckIn.status == "completed")
            )
            == 1
        )
        return await original(context)

    llm.support = observe_commit
    assert complete(client, auth_headers)["status"] == "completed"


def test_reports_cache_and_provider_failure(post_client, auth_headers):
    client, llm = post_client
    complete(client, auth_headers)
    url = "/api/v1/agents/post-workout/reports"
    first = client.post(url, headers=auth_headers, json={})
    assert first.status_code == 200, first.text
    assert first.json()["support"]["status"] == "available"
    assert len(llm.support_calls) == 1  # comment generated during confirmation is reused
    llm.fail_support = True
    failed = client.post(url, headers=auth_headers, json={"regenerateComment": True})
    assert failed.status_code == 200
    assert failed.json()["support"]["status"] == "unavailable"
    assert len(client.get(url, headers=auth_headers).json()) == 1
    llm.fail_support = False
    retried = client.post(url, headers=auth_headers, json={})
    assert retried.json()["support"]["status"] == "available"


def test_report_generation_without_checkins_and_no_auth(post_client, auth_headers):
    client, _ = post_client
    assert client.post("/api/v1/agents/post-workout/reports", headers=auth_headers, json={}).status_code == 200
    assert client.post("/api/v1/agents/post-workout/sessions", json={"requestId": str(uuid4())}).status_code == 401
    assert client.get("/api/v1/agents/post-workout/reports").status_code == 401
    assert client.get("/api/v1/agents/post-workout/feedback").status_code == 401


def test_future_workout_is_rejected(post_client, auth_headers):
    client, _ = post_client
    response = client.post(
        "/api/v1/agents/post-workout/sessions",
        headers=auth_headers,
        json={"requestId": str(uuid4()), "workoutEndedAt": (datetime.now(UTC) + timedelta(days=1)).isoformat()},
    )
    assert response.status_code == 422


def test_azure_sdk_uses_strict_schema_and_real_parser(monkeypatch):
    captured = []

    def handler(request):
        import json

        captured.append(json.loads(request.content))
        content = AnswerExtraction(
            score=7, choice=None, locations=[], text=None, needs_clarification=False, safety_observations=[]
        ).model_dump_json()
        return httpx.Response(
            200,
            json={
                "id": "test",
                "object": "chat.completion",
                "created": 0,
                "model": "chat-deployment",
                "choices": [
                    {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}
                ],
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            async with AsyncAzureOpenAI(
                azure_endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                api_version="2024-10-21",
                http_client=http_client,
            ) as azure:
                from app.agents.post_workout import llm as module

                monkeypatch.setattr(module, "get_async_azure_client", lambda: azure)
                result = await AzurePostWorkoutLLM().extract({"message": "7"})
                assert result.score == 7

    asyncio.run(run())
    schema = captured[0]["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"]["additionalProperties"] is False
    assert set(schema["schema"]["required"]) == set(AnswerExtraction.model_fields)


@pytest.mark.parametrize(
    "message",
    [
        "No chest pain and I can't breathe",
        "The chest pain is not gone",
        "I had chest pain yesterday and I have chest pain now",
    ],
)
def test_current_urgent_symptom_is_not_hidden_by_other_clauses(message):
    assert any(item.code in {"chest_discomfort", "severe_breathlessness"} for item in literal_observations(message))


def test_cropped_model_quote_cannot_hide_negation(post_client, auth_headers):
    client, llm = post_client
    session = turn(client, auth_headers, start(client, auth_headers), message="no")
    llm.extraction = AnswerExtraction(
        score=None,
        choice=None,
        locations=[],
        text=None,
        needs_clarification=True,
        safety_observations=[SafetyObservation(code="chest_discomfort", evidence="chest pain")],
    )
    session = turn(client, auth_headers, session, message="I have no chest pain")
    assert session["notice"] is None
    assert session["status"] == "in_progress"


def test_failed_extraction_does_not_advance_or_save_unconfirmed_answer(post_client, auth_headers):
    client, llm = post_client
    session = turn(client, auth_headers, start(client, auth_headers), message="no")

    async def fail(context):
        raise PostWorkoutModelError("Invalid structured output")

    llm.extract = fail
    path = f"/api/v1/agents/post-workout/sessions/{session['sessionId']}"
    failed = client.post(
        path + "/chat",
        headers=auth_headers,
        json={
            "requestId": str(uuid4()),
            "expectedVersion": session["version"],
            "message": "I would say seven",
        },
    )
    assert failed.status_code == 502
    current = client.get(path, headers=auth_headers).json()
    assert current["version"] == session["version"]
    assert current["draftFeedback"]["fatigueLevel"] is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"score": True},
        {"score": 11},
        {"score": "7"},
        {"score": 7.5},
        {"locations": [""]},
        {"extra_field": "unexpected"},
    ],
)
def test_extraction_rejects_invalid_types_and_extra_fields(overrides):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AnswerExtraction.model_validate(
            {
                "score": None,
                "choice": None,
                "locations": [],
                "text": None,
                "needs_clarification": False,
                "safety_observations": [],
                **overrides,
            }
        )

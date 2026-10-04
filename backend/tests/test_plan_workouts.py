import asyncio
from datetime import date
from types import SimpleNamespace

from app.agents.llm import StubLLM
from app.agents.plan.agent import PlanAgent
from app.schemas.plan import PlanExercise, TrainingPlan, Workout

MONDAY = date(2026, 10, 5)
WEDNESDAY = date(2026, 10, 7)


def workout(day: date, focus: str) -> Workout:
    exercise = PlanExercise(title="Squat", gif_url="", description="", sets=3, reps=10, estimated_time_minutes=20)
    return Workout(day=day.strftime("%A"), date=day, focus=focus, exercises=[exercise, exercise])


def save_plan(user_id: int, *workouts: Workout) -> PlanAgent:
    agent = PlanAgent(StubLLM())
    agent.save(user_id, TrainingPlan(workouts=list(workouts)))
    return agent


def test_done_removes_workout_and_starts_check_in(client, auth_headers):
    save_plan(1, workout(MONDAY, "Legs"), workout(WEDNESDAY, "Upper body"))

    res = client.post(f"/api/v1/agents/plan/workouts/{MONDAY}/done", headers=auth_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert [w["date"] for w in body["plan"]["workouts"]] == [str(WEDNESDAY)]
    assert body["checkIn"]["status"] == "in_progress"
    assert body["checkIn"]["draftFeedback"]["workoutType"] == "Legs"
    assert body["checkIn"]["draftFeedback"]["workoutDurationMinutes"] == 40

    saved = client.get("/api/v1/agents/plan", headers=auth_headers).json()
    assert [w["date"] for w in saved["workouts"]] == [str(WEDNESDAY)]


def test_done_unknown_date_is_404(client, auth_headers):
    save_plan(1, workout(MONDAY, "Legs"))
    client.post(f"/api/v1/agents/plan/workouts/{MONDAY}/done", headers=auth_headers)

    res = client.post(f"/api/v1/agents/plan/workouts/{MONDAY}/done", headers=auth_headers)
    assert res.status_code == 404


def test_regenerates_only_when_plan_is_finished(client, monkeypatch):
    user = SimpleNamespace(id=1, timezone="Europe/Warsaw")
    calls = []

    async def fake_generate(db, user, questionnaire, today):
        calls.append(today)
        return TrainingPlan(workouts=[])

    agent = save_plan(1, workout(MONDAY, "Legs"))
    monkeypatch.setattr(agent, "generate", fake_generate)

    assert asyncio.run(agent.regenerate_if_finished(None, user, object())) is None
    agent.complete_workout(1, MONDAY)
    assert asyncio.run(agent.regenerate_if_finished(None, user, None)) is None  # no questionnaire
    assert asyncio.run(agent.regenerate_if_finished(None, user, object())) is not None
    assert len(calls) == 1

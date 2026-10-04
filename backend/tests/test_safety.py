from datetime import UTC, datetime

import pytest

from app.agents.plan.health import OVERTRAINING_CACHE, health_summary
from app.agents.safety import health_flags_notice, medical_notice
from app.db.session import get_db
from app.main import app
from app.models import PostWorkoutCheckIn, User

TRAINING_CHAT = "/api/v1/agents/training/chat"
DIET_CHAT = "/api/v1/agents/diet/chat"


@pytest.mark.parametrize(
    ("message", "level", "code"),
    [
        ("I have chest pain right now", "urgent", "chest_discomfort"),
        ("Zemdlałam na siłowni", "urgent", "fainting"),
        ("I think I broke my wrist", "consultation", "serious_injury"),
        ("Mam złamaną rękę", "consultation", "serious_injury"),
        ("I tore my ACL, it's a torn ligament", "consultation", "serious_injury"),
        ("Bardzo źle się czuję od rana", "consultation", "feeling_very_unwell"),
        ("I've been vomiting all night", "consultation", "feeling_very_unwell"),
    ],
)
def test_medical_notice_detects_symptoms(message, level, code):
    notice = medical_notice(message)
    assert notice is not None and notice.level == level and code in notice.codes


@pytest.mark.parametrize(
    "message",
    ["I broke my diet yesterday", "Złamałam dietę", "Nie mam złamania", "No chest pain, just tired", "I feel great"],
)
def test_medical_notice_ignores_harmless_messages(message):
    assert medical_notice(message) is None


def test_chat_with_urgent_symptoms_returns_only_the_referral(client, auth_headers, complete_questionnaire):
    complete_questionnaire(auth_headers)
    res = client.post(TRAINING_CHAT, json={"message": "I have chest pain"}, headers=auth_headers).json()

    assert res["safety_notice"]["level"] == "urgent"
    assert "emergency services" in res["reply"] and "[stub]" not in res["reply"]


def test_chat_with_serious_injury_puts_the_referral_before_the_reply(client, auth_headers, complete_questionnaire):
    complete_questionnaire(auth_headers)
    res = client.post(TRAINING_CHAT, json={"message": "I broke my leg, what can I train?"}, headers=auth_headers).json()

    assert res["safety_notice"]["level"] == "consultation"
    assert res["reply"].startswith("This sounds like something a doctor should look at") and "[stub]" in res["reply"]


def test_questionnaire_with_urgent_symptoms_repeats_the_question(client, auth_headers):
    res = client.post(DIET_CHAT, json={"message": "I can't breathe"}, headers=auth_headers).json()

    assert res["safety_notice"]["level"] == "urgent" and res["question"]["key"] == "mainGoal"
    assert client.get("/api/v1/agents/diet/questionnaire", headers=auth_headers).json()["step"] == 0


def test_health_flags_notice():
    assert health_flags_notice(False, set()) is None
    assert health_flags_notice(True, set()).codes == ["overtraining"]
    notice = health_flags_notice(False, {"persistent_distress", "self_harm_risk"})
    assert notice.codes == ["self_harm_risk"] and "116 123" in notice.message


def db_and_user():
    db = next(app.dependency_overrides[get_db]())
    return db, db.query(User).one()


def add_check_in(db, user, code):
    db.add(
        PostWorkoutCheckIn(
            user_id=user.id,
            request_id="00000000-0000-0000-0000-000000000001",
            start_payload_hash="0" * 64,
            workout_ended_at=datetime.now(UTC),
            safety_observations=[{"code": code, "evidence": "I've been feeling down for weeks"}],
        )
    )
    db.commit()


def test_distress_in_a_recent_check_in_sets_the_flag_and_the_chat_banner(client, auth_headers, complete_questionnaire):
    complete_questionnaire(auth_headers)
    db, user = db_and_user()
    assert health_summary(db, user).mental_health_concern is False

    add_check_in(db, user, "persistent_distress")
    assert health_summary(db, user).mental_health_concern is True
    res = client.post(TRAINING_CHAT, json={"message": "What should I train today?"}, headers=auth_headers).json()
    assert res["safety_notice"]["codes"] == ["persistent_distress"]


def test_overtraining_flag_shows_in_the_chat_banner(client, auth_headers, complete_questionnaire):
    complete_questionnaire(auth_headers)
    _, user = db_and_user()
    OVERTRAINING_CACHE[user.id] = (datetime.now(UTC).date(), ["rhr", "sleep_minutes"])

    res = client.post(TRAINING_CHAT, json={"message": "What should I train today?"}, headers=auth_headers).json()
    assert res["safety_notice"]["codes"] == ["overtraining"]

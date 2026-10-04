import hashlib
import json
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agents.post_workout.questionnaire import active_questions, next_question
from app.agents.post_workout.safety import notice_for
from app.models import Message, PostWorkoutCheckIn, QuestionnaireState, User
from app.schemas.post_workout import CheckInResponse, PainFeedback, PostWorkoutFeedback, StartCheckIn, Support
from app.statistics.post_workout import utc

MAX_TURNS = 100


def payload_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def get_checkin(db: Session, user_id: int, checkin_id: str) -> PostWorkoutCheckIn:
    row = db.scalar(
        select(PostWorkoutCheckIn).where(PostWorkoutCheckIn.id == checkin_id, PostWorkoutCheckIn.user_id == user_id)
    )
    if row is None:
        raise HTTPException(404, "Post-workout check-in not found")
    return row


def feedback_for(row, *, confirmed: bool = False) -> PostWorkoutFeedback:
    answers = row.answers
    if confirmed:
        values = {
            key: getattr(row, attribute)
            for key, attribute in {
                "fatigue_level": "fatigue_level",
                "feeling_change": "feeling_change",
                "mood_level": "mood_level",
                "motivation_level": "motivation_level",
                "perceived_exertion_rating": "perceived_exertion_rating",
            }.items()
        }
        pain = PainFeedback(
            experienced=row.pain_experienced,
            intensity=row.pain_intensity,
            locations=row.pain_locations or [],
            description=row.pain_description,
        )
    else:
        values = {
            attribute: answers.get(key)
            for key, attribute in {
                "fatigueLevel": "fatigue_level",
                "feelingChange": "feeling_change",
                "moodLevel": "mood_level",
                "motivationLevel": "motivation_level",
                "perceivedExertionRating": "perceived_exertion_rating",
            }.items()
        }
        experienced = answers.get("painExperienced")
        pain = PainFeedback(
            experienced=experienced,
            intensity=0 if experienced is False else answers.get("painIntensity"),
            locations=(answers.get("painLocations") or []) if experienced is True else [],
            description=answers.get("_painDescription") if experienced is True else None,
        )
    return PostWorkoutFeedback(
        workout_ended_at=utc(row.workout_ended_at),
        workout_type=row.workout_type,
        workout_duration_minutes=row.workout_duration_minutes,
        pain=pain,
        **values,
    )


def response_for(row, reply: str | None = None, report_id: str | None = None) -> CheckInResponse:
    if report_id is None:
        for entry in reversed(list(row.processed_requests.values())):
            if entry["response"].get("reportId"):
                report_id = entry["response"]["reportId"]
                break
    questions = active_questions(row.answers)
    question = next_question(row.answers) if row.status == "in_progress" else None
    support = Support.model_validate(row.support) if row.support else None
    draft = feedback_for(row)
    notice = notice_for(row.safety_observations or [], draft.pain.intensity)
    if reply is None:
        if row.status == "interrupted":
            reply = notice.message if notice else "This check-in has been interrupted."
        elif row.status == "completed":
            reply = support.message if support else "Your post-workout feedback has been saved."
        elif row.status == "awaiting_confirmation":
            reply = "Please review your answers below. You can correct an answer or confirm to save your feedback."
        else:
            reply = question.text
    return CheckInResponse(
        session_id=row.id,
        version=row.version,
        status=row.status,
        step=sum(question.key in row.answers for question in questions),
        total=len(questions),
        reply=reply,
        question=question.out() if question else None,
        draft_feedback=draft,
        post_workout_feedback=feedback_for(row, confirmed=True) if row.status == "completed" else None,
        notice=notice,
        support=support,
        report_id=report_id,
    )


def create_checkin(db: Session, user_id: int, data: StartCheckIn) -> PostWorkoutCheckIn:
    fingerprint = payload_hash(data.model_dump(mode="json", exclude={"request_id"}))
    existing = db.scalar(
        select(PostWorkoutCheckIn).where(
            PostWorkoutCheckIn.user_id == user_id, PostWorkoutCheckIn.request_id == str(data.request_id)
        )
    )
    if existing is not None:
        if existing.start_payload_hash != fingerprint:
            raise HTTPException(409, "requestId was already used with a different start payload")
        return existing
    now = datetime.now(UTC)
    ended_at = utc(data.workout_ended_at) if data.workout_ended_at else now
    if ended_at > now + timedelta(minutes=5):
        raise HTTPException(422, "workoutEndedAt cannot be in the future")
    row = PostWorkoutCheckIn(
        user_id=user_id,
        request_id=str(data.request_id),
        start_payload_hash=fingerprint,
        workout_ended_at=ended_at,
        workout_type=data.workout_type,
        workout_duration_minutes=data.workout_duration_minutes,
    )
    db.add(row)
    try:
        db.flush()
        db.add(
            Message(
                user_id=user_id,
                agent="post_workout",
                post_workout_checkin_id=row.id,
                role="assistant",
                content=next_question({}).text,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(PostWorkoutCheckIn).where(
                PostWorkoutCheckIn.user_id == user_id, PostWorkoutCheckIn.request_id == str(data.request_id)
            )
        )
        if existing is None:
            raise
        if existing.start_payload_hash != fingerprint:
            raise HTTPException(409, "requestId was already used with a different start payload") from None
        return existing
    db.refresh(row)
    return row


def user_context(db: Session, user_id: int) -> dict:
    user = db.get(User, user_id)
    state = db.scalar(select(QuestionnaireState).where(QuestionnaireState.user_id == user_id))
    allowed = {"mainGoal", "experienceLevel", "injuriesAndLimitations", "intensityCheck"}
    return {
        "name": user.name,
        "reporting_frequency": user.post_workout_reporting_frequency,
        "timezone": user.timezone,
        "training_questionnaire": {key: value for key, value in state.answers.items() if key in allowed}
        if state is not None and state.completed_at is not None
        else {},
    }


def recent_messages(db: Session, user_id: int, checkin_id: str) -> list[dict]:
    rows = db.scalars(
        select(Message)
        .where(
            Message.user_id == user_id, Message.agent == "post_workout", Message.post_workout_checkin_id == checkin_id
        )
        .order_by(Message.id.desc())
        .limit(6)
    ).all()
    return [{"role": row.role, "content": row.content} for row in reversed(rows)]


def replay_turn(row, request_id: str, fingerprint: str) -> CheckInResponse | None:
    entry = row.processed_requests.get(request_id)
    if not entry:
        return None
    if entry["hash"] != fingerprint:
        raise HTTPException(409, "requestId was already used with a different turn payload")
    return CheckInResponse.model_validate(entry["response"])


def persist_turn(
    db: Session,
    user_id: int,
    checkin_id: str,
    expected_version: int,
    request_id: str,
    fingerprint: str,
    values: dict,
    user_message: str,
    reply: str | None,
    *,
    report_period: str,
    timezone: str,
) -> tuple[CheckInResponse, str | None, bool]:
    from app.services.post_workout_reports import ensure_report

    result = db.execute(
        update(PostWorkoutCheckIn)
        .where(
            PostWorkoutCheckIn.id == checkin_id,
            PostWorkoutCheckIn.user_id == user_id,
            PostWorkoutCheckIn.version == expected_version,
        )
        .values(**values, version=expected_version + 1)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        row = get_checkin(db, user_id, checkin_id)
        replay = replay_turn(row, request_id, fingerprint)
        if replay is not None:
            return replay, replay.report_id, False
        raise HTTPException(409, "Check-in changed; fetch the current session and retry with its version")
    row = get_checkin(db, user_id, checkin_id)
    db.refresh(row)
    report = None
    if row.status == "completed":
        report = ensure_report(
            db, user_id, report_period, timezone, utc(row.workout_ended_at).astimezone(ZoneInfo(timezone)).date()
        )
    response = response_for(row, reply=reply, report_id=report.id if report else None)
    assistant = Message(
        user_id=user_id,
        agent="post_workout",
        post_workout_checkin_id=checkin_id,
        role="assistant",
        content=response.reply,
    )
    db.add_all(
        [
            Message(
                user_id=user_id,
                agent="post_workout",
                post_workout_checkin_id=checkin_id,
                role="user",
                content=user_message,
            ),
            assistant,
        ]
    )
    db.flush()
    row.processed_requests = {
        **row.processed_requests,
        request_id: {
            "hash": fingerprint,
            "response": response.model_dump(mode="json", by_alias=True),
            "assistant_id": assistant.id,
        },
    }
    db.commit()
    return response, report.id if report else None, True


def finish_support(
    db: Session, user_id: int, checkin_id: str, version: int, request_id: str, support: Support, report_id: str | None
) -> CheckInResponse:
    row = db.scalar(
        select(PostWorkoutCheckIn)
        .where(PostWorkoutCheckIn.id == checkin_id, PostWorkoutCheckIn.user_id == user_id)
        .with_for_update()
    )
    db.refresh(row)
    if row.version != version:
        return response_for(row)
    entry = row.processed_requests[request_id]
    response = response_for(row, report_id=report_id)
    response.support = support
    response.reply = support.message
    row.support = support.model_dump(mode="json", by_alias=True)
    row.processed_requests = {
        **row.processed_requests,
        request_id: {
            **entry,
            "response": response.model_dump(mode="json", by_alias=True),
        },
    }
    db.execute(
        update(Message)
        .where(
            Message.id == entry["assistant_id"],
            Message.user_id == user_id,
            Message.post_workout_checkin_id == checkin_id,
        )
        .values(content=response.reply)
    )
    db.commit()
    return response

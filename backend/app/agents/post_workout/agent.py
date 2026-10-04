import copy
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from types import SimpleNamespace

import openai
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.agents.post_workout.llm import AzurePostWorkoutLLM, PostWorkoutLLM, PostWorkoutModelError
from app.agents.post_workout.questionnaire import BY_KEY, PAIN_DETAILS, next_question, parse_direct
from app.agents.post_workout.safety import literal_observations, notice_for, verified_observations
from app.models import PostWorkoutReport
from app.schemas.post_workout import AnswerExtraction, ChatTurn, CheckInResponse, Support
from app.services import post_workout as store
from app.services.post_workout_reports import report_response, selected_support
from app.statistics.post_workout import utc


class PostWorkoutAgent:
    name = "post_workout"

    def __init__(self, llm: PostWorkoutLLM):
        self.llm = llm

    async def run(self, db: Session, user_id: int, checkin_id: str, data: ChatTurn) -> CheckInResponse:
        row = store.get_checkin(db, user_id, checkin_id)
        request_id = str(data.request_id)
        fingerprint = store.payload_hash(data.model_dump(mode="json", exclude={"request_id"}))
        if replay := store.replay_turn(row, request_id, fingerprint):
            return replay
        if row.version != data.expected_version:
            raise HTTPException(409, "Check-in changed; fetch the current session and retry with its version")
        if len(row.processed_requests) >= store.MAX_TURNS:
            raise HTTPException(409, "Check-in turn limit reached; start a new check-in")
        if row.status == "interrupted":
            raise HTTPException(409, "This check-in was interrupted; follow the notice shown in the session")
        if row.status == "completed" and data.action not in {"confirm", "retry_support"}:
            raise HTTPException(409, "This check-in is already completed")
        if row.status == "completed" and data.action == "confirm":
            return store.response_for(row)
        profile = store.user_context(db, user_id)
        history = store.recent_messages(db, user_id, checkin_id)
        snapshot = SimpleNamespace(
            **{column.key: copy.deepcopy(getattr(row, column.key)) for column in row.__table__.columns}
        )
        db.rollback()  # Never keep a read transaction open while awaiting Azure.
        answers = dict(snapshot.answers)
        observations = {item["code"]: item for item in snapshot.safety_observations}
        reply = None
        values = {}
        should_generate_support = False

        if data.action == "retry_support":
            if snapshot.status != "completed":
                raise HTTPException(409, "Only completed check-ins can retry support")
            previous_support = Support.model_validate(snapshot.support) if snapshot.support else None
            if previous_support and previous_support.status == "available":
                raise HTTPException(409, "A personalised comment is already available")
            if (
                previous_support
                and previous_support.status == "pending"
                and previous_support.started_at
                and (datetime.now(UTC) - utc(previous_support.started_at) < timedelta(minutes=2))
            ):
                raise HTTPException(409, "Support is already being generated; fetch the session state")
            should_generate_support = True
        elif data.action == "confirm":
            if snapshot.status != "awaiting_confirmation" or next_question(answers) is not None:
                raise HTTPException(409, "Answer or skip the remaining questions before confirming")
            feedback = store.feedback_for(snapshot)
            values.update(
                {
                    key: value
                    for key, value in feedback.model_dump().items()
                    if key
                    in {
                        "fatigue_level",
                        "feeling_change",
                        "mood_level",
                        "motivation_level",
                        "perceived_exertion_rating",
                    }
                }
            )
            values.update(
                status="completed",
                completed_at=datetime.now(UTC),
                pain_experienced=feedback.pain.experienced,
                pain_intensity=feedback.pain.intensity,
                pain_locations=feedback.pain.locations,
                pain_description=feedback.pain.description,
            )
            should_generate_support = True
        else:
            question = BY_KEY.get(data.field_key) if data.action == "correct" else next_question(answers)
            if data.action == "correct" and (
                question is None
                or question.key not in answers
                or (question.key in PAIN_DETAILS and answers.get("painExperienced") is not True)
            ):
                raise HTTPException(422, "fieldKey must identify an answer already present in this check-in")
            literal = literal_observations(data.message or "")
            observations.update({item.code: item.model_dump() for item in literal})
            urgent = notice_for(list(observations.values()))
            if urgent is None or urgent.level != "urgent":
                if data.action == "skip":
                    if question is None:
                        raise HTTPException(409, "No question is waiting for an answer")
                    answers[question.key] = None
                else:
                    handled, value = parse_direct(question, data.message) if question else (False, None)
                    extraction = None
                    if not handled:
                        extraction = await self.llm.extract(
                            {
                                "question": question.out().model_dump(mode="json", by_alias=True)
                                if question
                                else {"key": "confirmation", "text": "Use confirm or correct to review these answers."},
                                "draft_answers": answers,
                                "recent_conversation": history,
                                "message": data.message,
                            }
                        )
                        verified = verified_observations(data.message, extraction.safety_observations)
                        observations.update({item.code: item.model_dump() for item in verified})
                        value = self.extracted_value(question, extraction) if question else None
                    if question and value is not None:
                        answers[question.key] = value
                        if question.key == "painLocations" and extraction:
                            answers["_painDescription"] = extraction.text
                    elif question:
                        reply = (
                            "Please give an explicit number from 0 to 10, or skip this question."
                            if (question.type == "scale")
                            else "I couldn't clearly match your answer. Please choose an option, clarify, or skip."
                        )
                    else:
                        reply = "Please review the draft, then send confirm or correct to finish this check-in."
            if answers.get("painExperienced") is not True:
                for key in (*PAIN_DETAILS, "_painDescription"):
                    answers.pop(key, None)
            current_notice = notice_for(list(observations.values()), answers.get("painIntensity"))
            status = (
                "interrupted"
                if current_notice and current_notice.level == "urgent"
                else ("in_progress" if next_question(answers) else "awaiting_confirmation")
            )
            if status == "interrupted":
                reply = current_notice.message
            values.update(answers=answers, safety_observations=list(observations.values()), status=status)

        if should_generate_support:
            values["support"] = Support(
                status="pending",
                message="Your feedback is saved. A comment is being generated.",
                started_at=datetime.now(UTC),
            ).model_dump(mode="json", by_alias=True)
        message = data.message if data.message is not None else data.action
        response, report_id, is_new = store.persist_turn(
            db,
            user_id,
            checkin_id,
            data.expected_version,
            request_id,
            fingerprint,
            values,
            message,
            reply,
            report_period=profile["reporting_frequency"],
            timezone=profile["timezone"],
        )
        if not should_generate_support or not is_new:
            return response
        report = report_response(db.get(PostWorkoutReport, report_id))
        context = {
            "profile": profile,
            "confirmed_feedback": response.post_workout_feedback.model_dump(mode="json", by_alias=True),
            "statistics": report.statistics.model_dump(mode="json", by_alias=True),
            "available_observations": [item.model_dump() for item in report.observations],
            "safety_notice": response.notice.model_dump(mode="json", by_alias=True) if response.notice else None,
        }
        db.rollback()
        try:
            result = await self.llm.support(context)
            support = selected_support(result, report.observations)
        except (openai.APIError, PostWorkoutModelError, HTTPException):
            support = Support(
                status="unavailable",
                message=("Your feedback has been saved. A personalised comment is unavailable right now."),
            )
        response = store.finish_support(db, user_id, checkin_id, response.version, request_id, support, report_id)
        report_row = db.get(PostWorkoutReport, report_id)
        if report_row.support is None or report_row.support.get("status") == "unavailable":
            report_row.support = support.model_dump(mode="json", by_alias=True)
            db.commit()
        return response

    @staticmethod
    def extracted_value(question, extraction: AnswerExtraction):
        if extraction.needs_clarification:
            return None
        if question.type == "scale":
            return extraction.score
        if question.key == "painExperienced":
            return {"yes": True, "no": False}.get(extraction.choice)
        if question.key == "feelingChange":
            return extraction.choice if extraction.choice in {"better", "same", "worse"} else None
        if question.key == "painLocations":
            return extraction.locations or None
        return None


@lru_cache
def get_post_workout_agent() -> PostWorkoutAgent:
    return PostWorkoutAgent(AzurePostWorkoutLLM())

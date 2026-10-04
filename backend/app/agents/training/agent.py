import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import BaseAgent, untrusted
from app.agents.llm import get_llm
from app.agents.safety import medical_notice
from app.agents.training import prompts
from app.agents.training.questionnaire import (
    MAX_NOTES,
    NONE,
    NOTE_KEYS,
    QUESTIONS,
    Question,
    build_result,
    format_question,
    parse_answer,
    question_text,
    validate,
)
from app.core.config import settings
from app.models import QuestionnaireState, User
from app.schemas.agent import AgentResponse
from app.schemas.post_workout import SafetyNotice
from app.schemas.questionnaire import QuestionnaireStatus


class TrainingAgent(BaseAgent):
    """Runs the questionnaire step by step first; after it's completed, chats as a regular trainer."""

    name = "training"
    system_prompt = prompts.SYSTEM_PROMPT
    use_health_flags = True

    async def run(self, db: Session, user: User, message: str, image: bytes | None = None) -> AgentResponse:
        state = self.get_state(db, user.id)
        if state is not None and state.completed_at is not None:
            return await super().run(db, user, message, image)

        if state is None:
            # The client already shows the first question (GET /questionnaire), so this message answers it.
            state = QuestionnaireState(user_id=user.id, step=0, answers={})
            db.add(state)

        return await self.answer_question(db, user, state, message)

    async def answer_question(self, db: Session, user: User, state: QuestionnaireState, message: str) -> AgentResponse:
        question = QUESTIONS[state.step]
        notice = medical_notice(message)
        if notice is not None and notice.level == "urgent":
            # Urgent symptoms come first: nothing is recorded and the same question waits for later.
            reply = f"{notice.message}\n\n{format_question(question, state.answers)}"
            return self.respond(db, user, message, reply, state, notice)

        values, notes, warning = parse_answer(question, message), "", ""
        if values is None:
            values, notes, warning = await self.extract_answer(question, message)
        prefix = "".join(f"{text}\n\n" for text in (notice and notice.message, warning) if text)
        if values is None and notes and question.key in NOTE_KEYS:
            values = [NONE]  # e.g. only an injury outside the options: keep it in the notes instead of re-asking

        if values is None:
            reply = f"{prefix}{prompts.NOT_UNDERSTOOD}\n\n{format_question(question, state.answers)}"
            return self.respond(db, user, message, reply, state, notice)

        state.answers[question.key] = values
        if question.key == "intensityCheck":
            state.answers["intensityNotes"] = notes
        elif question.key in NOTE_KEYS:
            state.answers[f"{question.key}Notes"] = notes
        state.step += 1

        if state.step < len(QUESTIONS):
            reply = prefix + format_question(QUESTIONS[state.step], state.answers)
            return self.respond(db, user, message, reply, state, notice)

        state.completed_at = datetime.now(UTC)
        result = build_result(state.answers).model_dump_json(by_alias=True, indent=2)
        self.result_path(user.id).write_text(result, encoding="utf-8")
        self.memory.add(user.id, f"Training questionnaire: {result}", source="questionnaire")
        return self.respond(db, user, message, prefix + prompts.COMPLETED, state, notice)

    async def extract_answer(self, question: Question, message: str) -> tuple[list[str] | None, str, str]:
        """LLM fallback for free-text answers; returns (values, notes, warning), values None when nothing valid."""
        system = prompts.EXTRACTION_PROMPT.format(
            question=question.text,
            options="\n".join(f"- {value}: {label}" for value, label in question.options.items()),
            cardinality="Multiple values are allowed." if question.multi else "Pick exactly one value.",
        )
        raw = await self.llm.complete(system, [{"role": "user", "content": message}], json_mode=True)
        try:
            data = json.loads(raw)
            values = validate(question, list(dict.fromkeys(data.get("values", []))))
            notes = str(data.get("notes", ""))[:MAX_NOTES]
            warning = str(data.get("warning", ""))[:MAX_NOTES]
        except (json.JSONDecodeError, AttributeError, TypeError):
            return None, "", ""
        return values, notes, warning

    def respond(
        self,
        db: Session,
        user: User,
        message: str,
        reply: str,
        state: QuestionnaireState,
        notice: SafetyNotice | None = None,
    ) -> AgentResponse:
        self.save_exchange(db, user, message, reply)  # commits the questionnaire state too
        if state.completed_at is not None:
            return AgentResponse(reply=reply, safety_notice=notice)
        question = QUESTIONS[state.step]
        return AgentResponse(
            reply=reply, question=question.to_out(question_text(question, state.answers)), safety_notice=notice
        )

    def get_state(self, db: Session, user_id: int) -> QuestionnaireState | None:
        return db.scalar(select(QuestionnaireState).where(QuestionnaireState.user_id == user_id))

    def get_status(self, db: Session, user_id: int) -> QuestionnaireStatus:
        state = self.get_state(db, user_id)
        step, answers = (state.step, state.answers) if state else (0, {})

        if state is not None and state.completed_at is not None:
            return QuestionnaireStatus(
                step=step, total=len(QUESTIONS), completed=True, training_questionnaire=build_result(answers)
            )
        question = QUESTIONS[step]
        return QuestionnaireStatus(
            step=step, total=len(QUESTIONS), completed=False, question=question.to_out(question_text(question, answers))
        )

    def reset(self, db: Session, user_id: int) -> None:
        # The previous result stays in Chroma memory; the system prompt always uses the current questionnaire.
        if state := self.get_state(db, user_id):
            db.delete(state)
            db.commit()
        self.result_path(user_id).unlink(missing_ok=True)

    def result_path(self, user_id: int) -> Path:
        path = Path(settings.questionnaire_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{user_id}.json"

    def build_context(self, db: Session, user: User, memories: list[str]) -> list[str]:
        context = super().build_context(db, user, memories)
        state = self.get_state(db, user.id)
        if state is not None and state.completed_at is not None:
            result = build_result(state.answers).model_dump_json(by_alias=True, indent=2)
            context.append(untrusted("training questionnaire", result))
        return context


@lru_cache
def get_training_agent() -> TrainingAgent:
    return TrainingAgent(get_llm())

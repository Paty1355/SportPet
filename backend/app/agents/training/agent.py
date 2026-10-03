import json
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.agents.llm import get_llm
from app.agents.training import prompts
from app.agents.training.questionnaire import (
    QUESTIONS,
    Question,
    build_result,
    format_question,
    parse_answer,
    question_text,
    validate,
)
from app.models import QuestionnaireState, User
from app.schemas.agent import AgentResponse
from app.schemas.questionnaire import QuestionnaireStatus


class TrainingAgent(BaseAgent):
    """Runs the questionnaire step by step first; after it's completed, chats as a regular trainer."""

    name = "training"
    system_prompt = prompts.SYSTEM_PROMPT

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
        values, notes = parse_answer(question, message), ""
        if values is None:
            values, notes = await self.extract_answer(question, message)

        if values is None:
            reply = f"{prompts.NOT_UNDERSTOOD}\n\n{format_question(question, state.answers)}"
            return self.respond(db, user, message, reply, state)

        state.answers[question.key] = values
        if question.key == "intensityCheck":
            state.answers["intensityNotes"] = notes
        state.step += 1

        if state.step < len(QUESTIONS):
            return self.respond(db, user, message, format_question(QUESTIONS[state.step], state.answers), state)

        state.completed_at = datetime.now(UTC)
        result = build_result(state.answers).model_dump_json(by_alias=True)
        self.memory.add(user.id, f"Training questionnaire: {result}", source="questionnaire")
        return self.respond(db, user, message, prompts.COMPLETED, state)

    async def extract_answer(self, question: Question, message: str) -> tuple[list[str] | None, str]:
        """LLM fallback for free-text answers; returns (None, "") when nothing valid comes back."""
        system = prompts.EXTRACTION_PROMPT.format(
            question=question.text,
            options="\n".join(f"- {value}: {label}" for value, label in question.options.items()),
            cardinality="Multiple values are allowed." if question.multi else "Pick exactly one value.",
        )
        raw = await self.llm.complete(system, [{"role": "user", "content": message}], json_mode=True)
        try:
            data = json.loads(raw)
            values = validate(question, list(dict.fromkeys(data.get("values", []))))
            notes = str(data.get("notes", ""))
        except (json.JSONDecodeError, AttributeError, TypeError):
            return None, ""
        return values, notes

    def respond(self, db: Session, user: User, message: str, reply: str, state: QuestionnaireState) -> AgentResponse:
        self.save_exchange(db, user, message, reply)  # commits the questionnaire state too
        if state.completed_at is not None:
            return AgentResponse(reply=reply)
        question = QUESTIONS[state.step]
        return AgentResponse(reply=reply, question=question.to_out(question_text(question, state.answers)))

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

    def build_system_prompt(self, db: Session, user: User, memories: list[str]) -> str:
        prompt = super().build_system_prompt(db, user, memories)
        state = self.get_state(db, user.id)
        if state is None or state.completed_at is None:
            return prompt
        result = build_result(state.answers).model_dump_json(by_alias=True, indent=2)
        return f"{prompt}\n\nTraining questionnaire:\n{result}"


@lru_cache
def get_training_agent() -> TrainingAgent:
    return TrainingAgent(get_llm())

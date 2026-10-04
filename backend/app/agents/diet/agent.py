import json
import re
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import BaseAgent, untrusted
from app.agents.diet import prompts
from app.agents.diet.questionnaire import NOTE_KEYS, QUESTIONS, build_result, format_question, question_text
from app.agents.diet_plan.agent import min_calories
from app.agents.llm import LLMClient, get_llm
from app.agents.safety import medical_notice
from app.agents.training.questionnaire import MAX_NOTES, NONE, Question, parse_answer, validate
from app.core.config import settings
from app.models import DietQuestionnaireState, User
from app.rag.knowledge_base import KnowledgeBase
from app.schemas.agent import AgentResponse
from app.schemas.post_workout import SafetyNotice
from app.schemas.questionnaire import DietQuestionnaireStatus

RAG_TOP_K = 4
MAX_CALORIES = 5000


class DietAgent(BaseAgent):

    name = "diet"
    system_prompt = prompts.SYSTEM_PROMPT
    use_health_flags = True

    def __init__(self, llm: LLMClient):
        super().__init__(llm)
        self.knowledge_base = KnowledgeBase(self.name)

    async def run(self, db: Session, user: User, message: str, image: bytes | None = None) -> AgentResponse:
        state = self.get_state(db, user.id)
        if state is not None and state.completed_at is not None:
            return await self.chat(db, user, message, image)

        if state is None:
            state = DietQuestionnaireState(user_id=user.id, step=0, answers={})
            db.add(state)

        return await self.answer_question(db, user, state, message)

    async def chat(self, db: Session, user: User, message: str, image: bytes | None = None) -> AgentResponse:
        memories = self.memory.search(user.id, message, k=self.memory_k)
        messages = self.build_messages(db, user, memories, message)

        system = self.build_system_prompt() + self.format_knowledge(message)
        reply, notice = await self.safe_reply(system, messages, message, image)

        self.save_exchange(db, user, message, reply)
        self.remember(user, message, reply)
        return AgentResponse(reply=reply, memories_used=memories, safety_notice=notice or self.flags_notice(db, user))

    def format_knowledge(self, query: str) -> str:
        chunks = self.knowledge_base.search(query, k=RAG_TOP_K)
        if not chunks:
            return ""
        excerpts = "\n\n".join(
            f"[{c.source}{f', p. {c.page}' if c.page is not None else ''}]\n{c.text}" for c in chunks
        )
        return f"\n\nReference excerpts:\n{excerpts}"

    async def answer_question(
        self, db: Session, user: User, state: DietQuestionnaireState, message: str
    ) -> AgentResponse:
        question = QUESTIONS[state.step]
        notice = medical_notice(message)
        if notice is not None and notice.level == "urgent":
            reply = f"{notice.message}\n\n{format_question(question, state.answers)}"
            return self.respond(db, user, message, reply, state, notice)

        values, notes, warning = parse_answer(question, message), "", ""
        if values is None and question.key == "calorieTarget":
            values, warning = custom_calories(message, user.sex)
        if values is None:
            values, notes, warning = await self.extract_answer(question, message)
        prefix = "".join(f"{text}\n\n" for text in (notice and notice.message, warning) if text)
        if values is None and notes and question.key in NOTE_KEYS:
            values = [NONE]

        if values is None:
            reply = f"{prefix}{prompts.NOT_UNDERSTOOD}\n\n{format_question(question, state.answers)}"
            return self.respond(db, user, message, reply, state, notice)

        state.answers[question.key] = values
        if question.key == "gentleCheck":
            state.answers["gentleNotes"] = notes
        elif question.key in NOTE_KEYS:
            state.answers[f"{question.key}Notes"] = notes
        state.step += 1

        if state.step < len(QUESTIONS):
            reply = prefix + format_question(QUESTIONS[state.step], state.answers)
            return self.respond(db, user, message, reply, state, notice)

        state.completed_at = datetime.now(UTC)
        result = build_result(state.answers).model_dump_json(by_alias=True, indent=2)
        self.result_path(user.id).write_text(result, encoding="utf-8")
        self.memory.add(user.id, f"Diet questionnaire: {result}", source="questionnaire")
        return self.respond(db, user, message, prefix + prompts.COMPLETED, state, notice)

    async def extract_answer(self, question: Question, message: str) -> tuple[list[str] | None, str, str]:
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
        state: DietQuestionnaireState,
        notice: SafetyNotice | None = None,
    ) -> AgentResponse:
        self.save_exchange(db, user, message, reply)
        if state.completed_at is not None:
            return AgentResponse(reply=reply, safety_notice=notice)
        question = QUESTIONS[state.step]
        return AgentResponse(
            reply=reply, question=question.to_out(question_text(question, state.answers)), safety_notice=notice
        )

    def get_state(self, db: Session, user_id: int) -> DietQuestionnaireState | None:
        return db.scalar(select(DietQuestionnaireState).where(DietQuestionnaireState.user_id == user_id))

    def get_status(self, db: Session, user_id: int) -> DietQuestionnaireStatus:
        state = self.get_state(db, user_id)
        step, answers = (state.step, state.answers) if state else (0, {})

        if state is not None and state.completed_at is not None:
            return DietQuestionnaireStatus(
                step=step, total=len(QUESTIONS), completed=True, diet_questionnaire=build_result(answers)
            )
        question = QUESTIONS[step]
        return DietQuestionnaireStatus(
            step=step, total=len(QUESTIONS), completed=False, question=question.to_out(question_text(question, answers))
        )

    def reset(self, db: Session, user_id: int) -> None:
        if state := self.get_state(db, user_id):
            db.delete(state)
            db.commit()
        self.result_path(user_id).unlink(missing_ok=True)

    def result_path(self, user_id: int) -> Path:
        path = Path(settings.questionnaire_dir) / self.name
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{user_id}.json"

    def build_context(self, db: Session, user: User, memories: list[str]) -> list[str]:
        context = super().build_context(db, user, memories)
        state = self.get_state(db, user.id)
        if state is not None and state.completed_at is not None:
            result = build_result(state.answers).model_dump_json(by_alias=True, indent=2)
            context.append(untrusted("diet questionnaire", result))
        return context


def custom_calories(message: str, sex: str | None) -> tuple[list[str] | None, str]:
    message = re.sub(r"(?<=\d)[ ,.](?=\d{3}\b)", "", message)
    match = re.search(r"\b\d{3,4}\b", message)
    if match is None or int(match[0]) > MAX_CALORIES:
        return None, ""
    target, minimum = int(match[0]), min_calories(sex)
    if target < minimum:
        return [str(minimum)], prompts.LOW_CALORIES.format(target=target, minimum=minimum)
    return [str(target)], ""


@lru_cache
def get_diet_agent() -> DietAgent:
    return DietAgent(get_llm())

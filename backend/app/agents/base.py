from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient
from app.memory.user_memory import UserMemory
from app.models import Message, User
from app.schemas.agent import AgentResponse


class BaseAgent:
    name: str
    system_prompt: str
    history_limit: int = 10
    memory_k: int = 5

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.memory = UserMemory(self.name)

    async def run(self, db: Session, user: User, message: str, image: bytes | None = None) -> AgentResponse:
        memories = self.memory.search(user.id, message, k=self.memory_k)
        history = self.get_history(db, user.id, limit=self.history_limit)

        messages = [{"role": m.role, "content": m.content} for m in history]
        messages.append({"role": "user", "content": message})

        reply = await self.llm.complete(self.build_system_prompt(user, memories), messages, image=image)

        db.add_all(
            [
                Message(user_id=user.id, agent=self.name, role="user", content=message),
                Message(user_id=user.id, agent=self.name, role="assistant", content=reply),
            ]
        )
        db.commit()
        self.remember(user, message, reply)

        return AgentResponse(reply=reply, memories_used=memories)

    def get_history(self, db: Session, user_id: int, limit: int) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.user_id == user_id, Message.agent == self.name)
            .order_by(Message.id.desc())
            .limit(limit)
        )
        return list(reversed(db.scalars(stmt).all()))

    def build_system_prompt(self, user: User, memories: list[str]) -> str:
        known = "\n".join(f"- {m}" for m in memories) or "(brak)"
        return f"{self.system_prompt}\n\nUżytkownik: {user.name or user.email}\nCo wiesz o użytkowniku:\n{known}"

    def remember(self, user: User, message: str, reply: str) -> None:
        # Na start zapisujemy wypowiedzi użytkownika; docelowo LLM może wyciągać z rozmowy konkretne fakty.
        self.memory.add(user.id, message, source="user_message")

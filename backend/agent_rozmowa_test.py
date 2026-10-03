"""Talk to the training agent in the terminal, without running the API.

Uses the real DB, Chroma and LLM from .env. Run from backend/:
    uv run python agent_rozmowa_test.py [email]
Commands: /status, /reset, /quit
"""

import asyncio
import sys

import app.models  # noqa: F401 – registers models in Base.metadata
from app.agents.training.agent import get_training_agent
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.schemas.user import UserCreate
from app.services.user_service import create_user, get_by_email


async def main(email: str) -> None:
    Base.metadata.create_all(bind=engine)
    agent = get_training_agent()

    with SessionLocal() as db:
        user = get_by_email(db, email) or create_user(db, UserCreate(email=email, password="password123"))
        print(f"Chatting as {user.email} (LLM: {type(agent.llm).__name__}). Commands: /status, /reset, /quit\n")

        status = agent.get_status(db, user.id)
        if status.question:
            print(f"agent> {status.question.text}")
            for i, option in enumerate(status.question.options, start=1):
                print(f"  {i}. {option.label}")

        while True:
            message = input("\nyou> ").strip()
            if not message:
                continue
            if message == "/quit":
                break
            if message == "/reset":
                agent.reset(db, user.id)
                print("Questionnaire reset.")
                continue
            if message == "/status":
                print(agent.get_status(db, user.id).model_dump_json(by_alias=True, indent=2))
                continue

            response = await agent.run(db, user, message)
            print(f"\nagent> {response.reply}")
            if response.memories_used:
                print(f"  (memories used: {response.memories_used})")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "test@example.com"))

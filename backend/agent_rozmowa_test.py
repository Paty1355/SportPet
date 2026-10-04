"""Talk to the training agent in the terminal, without running the API.

Uses the real DB, Chroma and LLM from .env. Run from backend/:
    uv run python agent_rozmowa_test.py [email]
Commands: /status, /plan, /reset, /quit
Once the questionnaire is completed, the plan agent generates a plan automatically.
"""

import asyncio
import sys

import app.models  # noqa: F401 – registers models in Base.metadata
from app.agents.plan.agent import PlanGenerationError, get_plan_agent
from app.agents.training.agent import get_training_agent
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.schemas.user import UserCreate
from app.services.user_service import create_user, get_by_email


async def print_plan(db, user, questionnaire) -> None:
    print("\nGenerating plan...")
    try:
        plan = await get_plan_agent().generate(db, user, questionnaire)
    except PlanGenerationError as e:
        print(f"Plan generation failed: {e}")
        return
    print(plan.model_dump_json(by_alias=True, indent=2))


async def main(email: str) -> None:
    Base.metadata.create_all(bind=engine)
    agent = get_training_agent()

    with SessionLocal() as db:
        user = get_by_email(db, email) or create_user(db, UserCreate(email=email, password="password123"))
        print(f"Chatting as {user.email} (LLM: {type(agent.llm).__name__}). Commands: /status, /plan, /reset, /quit\n")

        status = agent.get_status(db, user.id)
        was_completed = status.completed
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
            if message == "/plan":
                questionnaire = agent.get_status(db, user.id).training_questionnaire
                if questionnaire is None:
                    print("Complete the training questionnaire first.")
                else:
                    await print_plan(db, user, questionnaire)
                continue

            response = await agent.run(db, user, message)
            print(f"\nagent> {response.reply}")
            if response.memories_used:
                print(f"  (memories used: {response.memories_used})")

            status = agent.get_status(db, user.id)
            if status.completed and not was_completed and status.training_questionnaire:
                print("\nQuestionnaire:")
                print(status.training_questionnaire.model_dump_json(by_alias=True, indent=2))
                await print_plan(db, user, status.training_questionnaire)
            was_completed = status.completed


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "test@example.com"))

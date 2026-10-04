"""Talk to the training or diet agent in the terminal, without running the API.

Uses the real DB, Chroma and LLM from .env. Run from backend/:
    uv run python agent_rozmowa_test.py [email]
Commands: /status, /plan, /reset, /diet (switch between the training and diet agent), /quit
Once the questionnaire is completed, the matching plan agent generates a plan automatically.
"""

import asyncio
import sys

import app.models  # noqa: F401 – registers models in Base.metadata
from app.agents.diet.agent import get_diet_agent
from app.agents.diet_plan.agent import DietPlanGenerationError, get_diet_plan_agent
from app.agents.plan.agent import PlanGenerationError, get_plan_agent
from app.agents.training.agent import get_training_agent
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.schemas.user import UserCreate
from app.services.user_service import create_user, get_by_email

# mode -> (agent, status field holding the questionnaire result, plan agent, plan error)
MODES = {
    "training": (get_training_agent, "training_questionnaire", get_plan_agent, PlanGenerationError),
    "diet": (get_diet_agent, "diet_questionnaire", get_diet_plan_agent, DietPlanGenerationError),
}


async def print_plan(db, user, mode, questionnaire) -> None:
    print("\nGenerating plan...")
    _, _, get_planner, error = MODES[mode]
    try:
        plan = await get_planner().generate(db, user, questionnaire)
    except error as e:
        print(f"Plan generation failed: {e}")
        return
    print(plan.model_dump_json(by_alias=True, indent=2))


def print_question(status) -> None:
    if status.question:
        print(f"agent> {status.question.text}")
        for i, option in enumerate(status.question.options, start=1):
            print(f"  {i}. {option.label}")


async def main(email: str) -> None:
    Base.metadata.create_all(bind=engine)
    mode = "training"

    with SessionLocal() as db:
        user = get_by_email(db, email) or create_user(db, UserCreate(email=email, password="password123"))
        agent = MODES[mode][0]()
        print(f"As {user.email} (LLM: {type(agent.llm).__name__}). Cmds: /status, /plan, /reset, /diet, /quit\n")

        status = agent.get_status(db, user.id)
        was_completed = status.completed
        print_question(status)

        while True:
            message = input(f"\nyou[{mode}]> ").strip()
            if not message:
                continue
            if message == "/quit":
                break
            if message == "/diet":
                mode = "diet" if mode == "training" else "training"
                agent = MODES[mode][0]()
                status = agent.get_status(db, user.id)
                was_completed = status.completed
                print(f"Switched to the {mode} agent.")
                print_question(status)
                continue
            if message == "/reset":
                agent.reset(db, user.id)
                was_completed = False
                print("Questionnaire reset.")
                continue
            if message == "/status":
                print(agent.get_status(db, user.id).model_dump_json(by_alias=True, indent=2))
                continue
            if message == "/plan":
                questionnaire = getattr(agent.get_status(db, user.id), MODES[mode][1])
                if questionnaire is None:
                    print(f"Complete the {mode} questionnaire first.")
                else:
                    await print_plan(db, user, mode, questionnaire)
                continue

            response = await agent.run(db, user, message)
            print(f"\nagent> {response.reply}")
            if response.memories_used:
                print(f"  (memories used: {response.memories_used})")

            status = agent.get_status(db, user.id)
            questionnaire = getattr(status, MODES[mode][1])
            if status.completed and not was_completed and questionnaire:
                print("\nQuestionnaire:")
                print(questionnaire.model_dump_json(by_alias=True, indent=2))
                await print_plan(db, user, mode, questionnaire)
            was_completed = status.completed


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "test@example.com"))

# Diet agent (clone of the gym agent) + separate RAG folder

## Findings
- Gym agent = `BaseAgent` subclass (`agents/training/`): questionnaire state machine → then chat with Chroma memory + history. Router `router_training.py` (`/agents/training/chat|history`) and `router_questionnaire.py` (`/agents/training/questionnaire` GET/DELETE). DB table `training_questionnaires`, schema `TrainingQuestionnaire`, JSON result in `settings.questionnaire_dir`.
- Azure keys: `get_llm()` + `settings.azure_*` (shared). The diet agent uses the same call, so **no new env vars / config**; memory collection is derived from the agent name (`diet_memory`).
- RAG: `KnowledgeBase(name)` + `python -m app.rag.ingest --dir ... --name ...`. The gym agent never queries it (only the ingest CLI uses it), so retrieval is new code and goes into the diet agent only.

## Changes
1. `app/agents/base.py`: add hook `knowledge(message) -> str` (default `""`); `run` appends it to the system prompt. Gym behaviour unchanged.
2. `app/agents/diet/{__init__,agent,prompts,questionnaire}.py`: `DietAgent` (`name = "diet"`), `get_diet_agent()`. Reuses generic `Question`, `parse_answer`, `validate` from the training module; own questions, recap, `build_result`. `knowledge()` = `KnowledgeBase("diet").search(message, k=4)` formatted with source/page. Result JSON stored in `<questionnaire_dir>/diet/<user_id>.json`.
3. `app/models/questionnaire.py`: new `DietQuestionnaireState` (table `diet_questionnaires`, same columns); registered in `models/__init__.py`.
4. `app/schemas/questionnaire.py`: `DietQuestionnaire`, `DietQuestionnaireStatus` (camelCase like the gym one).
5. `app/api/v1/router_diet.py` (`/agents/diet/chat`, `/history`, `/questionnaire` GET/DELETE) registered in `router.py`.
6. New folder `backend/docs_RAG_diet/` (with `.gitkeep`) for your PDFs. Ingest: `uv run python -m app.rag.ingest --dir docs_RAG_diet --name diet`. Check Dockerfile/.dockerignore include it.
7. `tests/test_diet.py`: questionnaire flow + result JSON, retrieval injected into the prompt (fake embeddings), user isolation. `backend/README.md`: API table + RAG section.

## Draft diet questionnaire (10 questions, English; you review)
mainGoal (weight_loss / muscle_gain / maintenance / healthy_habits) · dietType (omnivore / vegetarian / vegan / pescatarian) · allergiesAndIntolerances, multi (gluten / lactose / nuts / eggs / none) · dislikedFoods, multi (fish / red_meat / dairy / vegetables / none) · mealsPerDay (3 / 4 / 5) · cookingTimeMinutes (15 / 30 / 60) · activityLevel (sedentary / light / moderate / high) · medicalConditions, multi (diabetes / hypertension / thyroid / pregnancy_breastfeeding / none) · eatingHabits (skip_breakfast / late_night_snacking / emotional_eating / regular) · gentleCheck (gradual changes vs. standard pace; cautious flag also triggered by medical conditions).

## Risk
Diet advice touches health; the prompt tells the model to defer to a doctor/dietitian for medical conditions. No new dependencies, no config/env changes, gym agent behaviour untouched.

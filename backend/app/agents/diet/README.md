# Diet agent

Dietitian chat agent. Clone of the gym (`training`) agent: an 11-question questionnaire first, then free chat with per-user Chroma memory,
message history and, unlike the gym agent, **RAG retrieval** from its own document folder. The gym agent is untouched; the two share only
generic helpers (`Question`, `parse_answer`, `validate`) imported from `app/agents/training/questionnaire.py`.

## Flow

1. `GET /api/v1/agents/diet/questionnaire` returns the current question (step 0 for a new user).
2. Each `POST /api/v1/agents/diet/chat` message answers the current question: an option value, a 1-based number, an exact label, or
   comma/semicolon separated for multi-choice. Free text goes to the LLM extraction fallback; if nothing valid comes back the question is repeated.
3. After the last question the result is stored (table `diet_questionnaires`, JSON in `<QUESTIONNAIRE_DIR>/diet/<user_id>.json`,
   and in Chroma memory) and the agent switches to normal chat.
4. In chat, the system prompt contains the questionnaire result, remembered facts and the top 4 chunks retrieved from the `diet` knowledge base
   (`[source, p. N]` + text).
5. `POST /api/v1/agents/diet-plan` (`app/agents/diet_plan/`, the counterpart of the gym `plan` agent) builds a 7-day meal plan from the questionnaire,
   the 14-day health summary (`app/agents/plan/health.py`) and the top 6 `diet` RAG chunks. Each day must have `mealsPerDay` meals, otherwise 502.
   `check_plan` also rejects plans below the healthy calorie minimum (1200 kcal for women, 1500 otherwise), more than 10% off
   `calorieTarget`, or with meals containing the user's allergens or foods excluded by the diet type; the LLM gets one retry, then 502.
   The plan is saved to `<DIET_PLAN_DIR>/<user_id>.json` (default `./data/diet_plans`). No post-meal feedback yet.

## Endpoints (JWT required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/agents/diet/chat` | answer the current question / chat (`{"message": "..."}`) |
| GET | `/agents/diet/history?limit=50` | message history |
| GET | `/agents/diet/questionnaire` | progress, current question, or final result (`dietQuestionnaire`) |
| DELETE | `/agents/diet/questionnaire` | reset the questionnaire (204) |
| POST | `/agents/diet-plan` | generate the weekly diet plan (409 without a completed questionnaire, 502 on invalid LLM output) |
| GET | `/agents/diet-plan` | last generated plan (404 if none) |

## Questionnaire

`mainGoal`, `dietType`, `allergiesAndIntolerances`*, `dislikedFoods`*, `mealsPerDay`, `cookingTimeMinutes`, `activityLevel`,
`calorieTarget`, `medicalConditions`*, `eatingHabits`*, `gentleCheck` (\* multi-choice, `none` option yields an empty list).
`calorieTarget` is `null` for "calculate it for me", or a number: an option or one typed by the user (e.g. "1,700 kcal"); a target below
the healthy minimum is raised to it with a warning. Free-text allergies and conditions outside the options end up in `healthNotes`.
The last question recaps the answers and
recommends a gradual start when a medical condition or emotional eating was selected. Options live in `questionnaire.py` (`QUESTIONS`) and must
match the `Literal`s in `DietQuestionnaire` (`app/schemas/questionnaire.py`); a test checks this.

## RAG documents

Put PDF/TXT files in [`backend/docs_RAG_diet/`](../../../docs_RAG_diet/) and ingest them (from `backend/`):

```bash
uv run python -m app.rag.ingest --dir docs_RAG_diet --name diet          # add/update files
uv run python -m app.rag.ingest --dir docs_RAG_diet --name diet --reset  # rebuild the collection
```

Collection: `diet_docs_<embedding deployment>`; memory: `diet_memory_<embedding deployment>`. Until documents are ingested, retrieval returns nothing
and the agent answers without excerpts.

## Configuration

Only `DIET_PLAN_DIR` (diet plan JSON files). It uses the same Azure OpenAI configuration as the other agents (`AZURE_OPENAI_*` in `backend/.env`, see `.env.example`)
via `get_llm()`; without Azure it falls back to the stub LLM.

## Files

- `agent.py`: `DietAgent`, `get_diet_agent()`; `questionnaire.py`: questions, recap, `build_result`; `prompts.py`: system and extraction prompts.
- `app/agents/diet_plan/`: `DietPlanAgent`, `get_diet_plan_agent()`, `prompts.py`; schema `app/schemas/diet_plan.py`.
- Routers: `router_diet.py` (chat, history), `router_diet_questionnaire.py`, `router_diet_plan.py`. Model: `DietQuestionnaireState`.
  Tests: `tests/test_diet.py`.

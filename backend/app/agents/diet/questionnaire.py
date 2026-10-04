from app.agents.training.questionnaire import NONE, Question
from app.schemas.questionnaire import DietQuestionnaire, GentleCheck

QUESTIONS: list[Question] = [
    Question(
        "mainGoal",
        "What is your main nutrition goal?",
        {
            "weight_loss": "Weight loss / fat reduction",
            "muscle_gain": "Building muscle",
            "maintenance": "Maintaining my current weight",
            "healthy_habits": "Eating healthier in general",
        },
    ),
    Question(
        "dietType",
        "Which best describes the way you eat?",
        {
            "omnivore": "I eat everything",
            "vegetarian": "Vegetarian",
            "vegan": "Vegan",
            "pescatarian": "Pescatarian (fish, no meat)",
        },
    ),
    Question(
        "allergiesAndIntolerances",
        "Do you have any food allergies or intolerances?",
        {
            "gluten": "Gluten",
            "lactose": "Lactose / dairy",
            "nuts": "Nuts",
            "eggs": "Eggs",
            NONE: "None of these",
        },
        multi=True,
    ),
    Question(
        "dislikedFoods",
        "Are there foods you truly dislike and would rather avoid?",
        {
            "fish": "Fish",
            "red_meat": "Red meat",
            "dairy": "Dairy",
            "vegetables": "Vegetables",
            NONE: "None of these",
        },
        multi=True,
    ),
    Question(
        "mealsPerDay",
        "How many meals a day suit you best?",
        {"3": "3 meals", "4": "4 meals", "5": "5 meals"},
    ),
    Question(
        "cookingTimeMinutes",
        "How much time can you spend cooking on a typical day?",
        {"15": "Up to 15 minutes", "30": "About 30 minutes", "60": "An hour or more"},
    ),
    Question(
        "activityLevel",
        "How active are you during a typical week?",
        {
            "sedentary": "Mostly sitting, little exercise",
            "light": "Light activity, 1-2 workouts a week",
            "moderate": "Moderate, 3-4 workouts a week",
            "high": "High, 5+ workouts or a physical job",
        },
    ),
    Question(
        "calorieTarget",
        "Do you have a daily calorie target in mind?",
        {
            "auto": "No, calculate it for me",
            "1500": "About 1500 kcal",
            "1800": "About 1800 kcal",
            "2000": "About 2000 kcal",
            "2500": "About 2500 kcal",
        },
    ),
    Question(
        "medicalConditions",
        "Do you have any health conditions that affect your diet?",
        {
            "diabetes": "Diabetes / insulin resistance",
            "hypertension": "High blood pressure",
            "thyroid": "Thyroid condition",
            "pregnancy_breastfeeding": "Pregnant or breastfeeding",
            NONE: "I'm fully healthy",
        },
        multi=True,
    ),
    Question(
        "eatingHabits",
        "Do any of these eating habits sound like you?",
        {
            "skip_breakfast": "I often skip breakfast",
            "late_night_snacking": "Late-night snacking",
            "emotional_eating": "Eating when stressed or emotional",
            NONE: "None of these",
        },
        multi=True,
    ),
    Question(
        "gentleCheck",
        "Would you like to change your diet gradually, so the plan isn't too strict at the start?",
        {
            "gradual": "Yes, start with small gentle changes",
            "standard": "No, I'm ready for a standard plan",
        },
    ),
]

CAUTION_FLAGS = {"diabetes", "hypertension", "thyroid", "pregnancy_breastfeeding", "emotional_eating"}
NOTE_KEYS = ("allergiesAndIntolerances", "medicalConditions")


def question_text(question: Question, answers: dict) -> str:
    if question.key != "gentleCheck":
        return question.text

    recap = "\n".join(
        f"- {q.text} {', '.join(q.options.get(v, f'{v} kcal') for v in answers[q.key])}"
        for q in QUESTIONS
        if q.key in answers
    )
    text = f"Here's what I know so far:\n{recap}\n\n{question.text}"
    if any(v in CAUTION_FLAGS for values in answers.values() if isinstance(values, list) for v in values):
        text += "\nBased on your answers, I'd recommend a gradual start."
    return text


def format_question(question: Question, answers: dict) -> str:
    options = "\n".join(f"{i}. {label}" for i, label in enumerate(question.options.values(), start=1))
    hint = "\n(You can pick more than one.)" if question.multi else ""
    return f"{question_text(question, answers)}\n{options}{hint}"


def build_result(answers: dict) -> DietQuestionnaire:
    def one(key: str) -> str:
        return answers[key][0]

    def many(key: str) -> list[str]:
        return [v for v in answers[key] if v != NONE]

    calorie_target = answers.get("calorieTarget", ["auto"])[0]

    return DietQuestionnaire(
        main_goal=one("mainGoal"),
        diet_type=one("dietType"),
        allergies_and_intolerances=many("allergiesAndIntolerances"),
        disliked_foods=many("dislikedFoods"),
        meals_per_day=int(one("mealsPerDay")),
        cooking_time_minutes=int(one("cookingTimeMinutes")),
        activity_level=one("activityLevel"),
        calorie_target=None if calorie_target == "auto" else int(calorie_target),
        medical_conditions=many("medicalConditions"),
        eating_habits=many("eatingHabits"),
        gentle_check=GentleCheck(gradual_start=one("gentleCheck") == "gradual", notes=answers.get("gentleNotes", "")),
        health_notes="; ".join(n for k in NOTE_KEYS if (n := answers.get(f"{k}Notes"))),
    )

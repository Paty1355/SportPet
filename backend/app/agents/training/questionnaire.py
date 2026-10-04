import re
from dataclasses import dataclass

from app.schemas.questionnaire import IntensityCheck, OptionOut, QuestionOut, TrainingQuestionnaire

NONE = "none"
MAX_NOTES = 300


@dataclass(frozen=True)
class Question:
    key: str
    text: str
    options: dict[str, str]
    multi: bool = False

    def to_out(self, text: str | None = None) -> QuestionOut:
        return QuestionOut(
            key=self.key,
            text=text or self.text,
            options=[OptionOut(value=v, label=label) for v, label in self.options.items()],
            multi=self.multi,
        )


QUESTIONS: list[Question] = [
    Question(
        "mainGoal",
        "What is your main goal at the gym?",
        {
            "weight_loss": "Weight loss / fat reduction",
            "toning": "Toning and building muscle",
            "postpartum": "Getting back in shape after pregnancy",
            "general_fitness": "Improving overall fitness",
        },
    ),
    Question(
        "experienceLevel",
        "How would you rate your current experience with strength training?",
        {
            "beginner": "Complete beginner",
            "returning": "Returning after a long break",
            "intermediate": "Intermediate",
            "regular": "I train regularly",
        },
    ),
    Question(
        "priorityBodyParts",
        "Are there specific body parts you want to focus on the most?",
        {
            "glutes": "Glutes and legs",
            "core": "Flat stomach and core",
            "back_arms": "Strong back and arms",
            "full_body": "Balanced full-body training",
        },
        multi=True,
    ),
    Question(
        "likedExercises",
        "Which types of movement or exercises do you enjoy the most?",
        {
            "weights": "Free weights",
            "machines": "Machines",
            "cardio": "Cardio / treadmill",
            "bodyweight": "Bodyweight classes",
        },
        multi=True,
    ),
    Question(
        "dislikedExercises",
        "Are there any exercises you truly dislike and would rather avoid?",
        {
            "burpees": "Burpees",
            "running": "Running",
            "jumping": "Jumps / plyometrics",
            "heavy_squats": "Heavy squats",
            NONE: "None of these",
        },
        multi=True,
    ),
    Question(
        "injuriesAndLimitations",
        "Do you have any pain, injuries or post-pregnancy limitations?",
        {
            "back": "Lower back / neck pain",
            "knees": "Sensitive knees",
            "diastasis": "Diastasis recti",
            NONE: "I'm fully healthy",
        },
        multi=True,
    ),
    Question(
        "preferredDays",
        "Which days of the week is it easiest for you to find time to train?",
        {
            "mwf": "Monday / Wednesday / Friday",
            "weekends": "Weekends only",
            "any_weekdays": "Any 3 weekdays",
            "flexible": "Flexible schedule",
        },
    ),
    Question(
        "workoutDurationMinutes",
        "How much time can you spend on a single gym visit at most?",
        {
            "40": "Quick 30-40 minutes",
            "60": "Standard 45-60 minutes",
            "90": "More than an hour",
        },
    ),
    Question(
        "lifestyleAndStress",
        "What does your typical day look like, and how stressful is it?",
        {
            "desk_stress": "8h at a desk + high stress",
            "active": "Constantly moving and caring for a child",
            "physical_work": "Physical work",
            "balanced": "Calm and balanced",
        },
    ),
    Question(
        "intensityCheck",
        "Would you like to start slowly and build up gradually, so the training isn't too fast or too intense?",
        {
            "cautious": "Yes, start slow and gentle",
            "standard": "No, I'm ready for a standard pace",
        },
    ),
]

DAYS_PER_WEEK = {"mwf": 3, "weekends": 2, "any_weekdays": 3, "flexible": 3}
CAUTION_FLAGS = {"postpartum", "beginner", "back", "knees", "diastasis"}
NOTE_KEYS = ("injuriesAndLimitations",)


def parse_answer(question: Question, text: str) -> list[str] | None:
    labels = {label.lower(): value for value, label in question.options.items()}
    keys = list(question.options)
    values: list[str] = []

    for token in (t.strip().lower() for t in re.split(r"[,;]", text) if t.strip()):
        if token in question.options:
            value = token
        elif token.isdigit() and 1 <= int(token) <= len(keys):
            value = keys[int(token) - 1]
        elif token in labels:
            value = labels[token]
        else:
            return None
        if value not in values:
            values.append(value)

    return validate(question, values)


def validate(question: Question, values: list[str]) -> list[str] | None:
    if not values or any(v not in question.options for v in values):
        return None
    if not question.multi and len(values) > 1:
        return None
    return values


def question_text(question: Question, answers: dict) -> str:
    if question.key != "intensityCheck":
        return question.text

    recap = "\n".join(
        f"- {q.text} {', '.join(q.options[v] for v in answers[q.key])}" for q in QUESTIONS if q.key in answers
    )
    text = f"Here's what I know so far:\n{recap}\n\n{question.text}"
    if any(v in CAUTION_FLAGS for values in answers.values() if isinstance(values, list) for v in values):
        text += "\nBased on your answers, I'd recommend a cautious start."
    return text


def format_question(question: Question, answers: dict) -> str:
    options = "\n".join(f"{i}. {label}" for i, label in enumerate(question.options.values(), start=1))
    hint = "\n(You can pick more than one.)" if question.multi else ""
    return f"{question_text(question, answers)}\n{options}{hint}"


def build_result(answers: dict) -> TrainingQuestionnaire:
    def one(key: str) -> str:
        return answers[key][0]

    def many(key: str) -> list[str]:
        return [v for v in answers[key] if v != NONE]

    return TrainingQuestionnaire(
        main_goal=one("mainGoal"),
        experience_level=one("experienceLevel"),
        priority_body_parts=many("priorityBodyParts"),
        liked_exercises=many("likedExercises"),
        disliked_exercises=many("dislikedExercises"),
        injuries_and_limitations=many("injuriesAndLimitations"),
        preferred_days=one("preferredDays"),
        training_days_per_week=DAYS_PER_WEEK[one("preferredDays")],
        workout_duration_minutes=int(one("workoutDurationMinutes")),
        lifestyle_and_stress=one("lifestyleAndStress"),
        intensity_check=IntensityCheck(
            cautious_start=one("intensityCheck") == "cautious",
            notes=answers.get("intensityNotes", ""),
        ),
        health_notes="; ".join(n for k in NOTE_KEYS if (n := answers.get(f"{k}Notes"))),
    )

from pathlib import Path
from urllib.parse import quote

from app.schemas.questionnaire import DislikedExercise, Injury, TrainingQuestionnaire

# The exercise catalogue is the set of gifs: exercise name = file name without ".gif".
GIF_DIR = Path(__file__).resolve().parents[1] / "training" / "exercises"
GIF_URL_PREFIX = "/static/exercises"

# Risky exercises excluded up front when the user has any of these injuries or dislikes; the LLM handles the rest.
AVOID: dict[str, set[Injury | DislikedExercise]] = {
    "Burpees": {"burpees", "jumping", "knees", "diastasis"},
    "Jump Squats": {"jumping", "knees", "diastasis"},
    "Jumping Jacks": {"jumping", "knees"},
    "Jump Rope": {"jumping", "knees"},
    "Ice Skaters": {"jumping", "knees"},
    "Barbell Back Squat": {"heavy_squats", "knees", "back"},
    "Squat": {"heavy_squats", "knees"},
    "Box Squat": {"heavy_squats"},
    "Thrusters": {"knees", "back"},
    "Bulgarian Split Squat": {"knees"},
    "Walking Lunges": {"knees"},
    "Weighted Walking Lunges": {"knees"},
    "Leg Extension": {"knees"},
    "Deadlift": {"back"},
    "Conventional Deadlift": {"back"},
    "Barbell Dead Lifts": {"back"},
    "Rack Pull": {"back"},
    "Stiff Leg Deadlift": {"back"},
    "Kettlebell Swings": {"back"},
    "V-ups": {"diastasis", "back"},
    "Tuck Ups": {"diastasis"},
    "Abdominal Crunch": {"diastasis"},
    "Weighted Crunch": {"diastasis", "back"},
    "Oblique Crunches": {"diastasis"},
    "Side Crunch": {"diastasis"},
    "Bicycles": {"diastasis"},
    "Russian Twist": {"diastasis", "back"},
    "Incline Sit-Ups": {"diastasis", "back"},
    "Exercise Ball Crunches": {"diastasis"},
    "Exercise Ball Pikes": {"diastasis"},
    "Cable Crunches (Allahs)": {"diastasis"},
    "Hanging Leg Raise": {"diastasis", "back"},
    "Leg Lifts": {"diastasis", "back"},
    "Mountain Climbers": {"diastasis"},
    "Plank": {"diastasis"},
    "Front Plank": {"diastasis"},
    "High Plank": {"diastasis"},
}


def available_exercises() -> list[str]:
    """Read on every call, so a newly added gif is available right away."""
    return sorted(p.stem for p in GIF_DIR.glob("*.gif"))


def allowed_exercises(questionnaire: TrainingQuestionnaire) -> list[str]:
    excluded = {*questionnaire.injuries_and_limitations, *questionnaire.disliked_exercises}
    return [name for name in available_exercises() if not excluded & AVOID.get(name, set())]


def exercise_title(name: str) -> str:
    # Some gif names list alternative names joined with " lub " ("or"); show the first one.
    return name.split(" lub ")[0]


def gif_url(name: str) -> str:
    return f"{GIF_URL_PREFIX}/{quote(name)}.gif"

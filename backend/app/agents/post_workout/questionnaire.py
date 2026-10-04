import re
from dataclasses import dataclass

from app.schemas.post_workout import CheckInQuestion, QuestionOption


@dataclass(frozen=True)
class Question:
    key: str
    text: str
    type: str
    options: tuple[tuple[str, str], ...] = ()

    def out(self) -> CheckInQuestion:
        return CheckInQuestion(
            key=self.key,
            text=self.text,
            type=self.type,
            options=[QuestionOption(value=value, label=label) for value, label in self.options],
            min_value=0 if self.type == "scale" else None,
            max_value=10 if self.type == "scale" else None,
        )


QUESTIONS = [
    Question(
        "painExperienced",
        "Did you feel any pain during your workout, or do you feel pain now?",
        "choice",
        (("yes", "Yes"), ("no", "No")),
    ),
    Question(
        "painLocations", "Where do you feel pain? You can name more than one area and describe it briefly.", "text"
    ),
    Question(
        "painIntensity", "How strong is the pain, from 0 (no pain) to 10 (the strongest you can imagine)?", "scale"
    ),
    Question("fatigueLevel", "How tired do you feel now, from 0 (not tired) to 10 (extremely tired)?", "scale"),
    Question(
        "feelingChange",
        "Compared with before your workout, do you feel better, the same, or worse?",
        "choice",
        (("better", "Better"), ("same", "The same"), ("worse", "Worse")),
    ),
    Question("moodLevel", "How is your mood now, from 0 (very low) to 10 (very good)?", "scale"),
    Question(
        "motivationLevel",
        "How motivated do you feel about your next workout, from 0 (not at all) to 10 (very)?",
        "scale",
    ),
    Question(
        "perceivedExertionRating",
        "How demanding was the whole workout, from 0 (no effort) to 10 (maximum effort)?",
        "scale",
    ),
]
BY_KEY = {question.key: question for question in QUESTIONS}
PAIN_DETAILS = {"painLocations", "painIntensity"}


def active_questions(answers: dict) -> list[Question]:
    return [
        question for question in QUESTIONS if question.key not in PAIN_DETAILS or answers.get("painExperienced") is True
    ]


def next_question(answers: dict) -> Question | None:
    return next((question for question in active_questions(answers) if question.key not in answers), None)


def parse_direct(question: Question, message: str) -> tuple[bool, object]:
    text = message.strip().casefold()
    if question.type == "scale" and re.fullmatch(r"\d{1,2}", text):
        return True, int(text) if 0 <= int(text) <= 10 else None
    if question.key == "painExperienced":
        if text in {"yes", "tak"}:
            return True, True
        if text in {"no", "nie"}:
            return True, False
    if question.key == "feelingChange":
        values = {
            "better": "better",
            "same": "same",
            "worse": "worse",
            "lepiej": "better",
            "tak samo": "same",
            "gorzej": "worse",
        }
        if text in values:
            return True, values[text]
    return False, None

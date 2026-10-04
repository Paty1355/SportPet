"""Doctor referral for chat agents and questionnaires; the LLM prompts cover what these literal patterns miss."""

import re

from app.agents.post_workout.safety import CLAUSE_BOUNDARY, literal_observations, normalized, notice_for
from app.schemas.post_workout import SafetyNotice

# Body parts make "broke my diet" / "złamałam dietę" not count as a fracture.
BODY = r"(?:arm|leg|wrist|ankle|foot|hand|finger|toe|ribs?|bone|nose|collarbone|hip|knee|shoulder|back|neck)"
PL_BODY = r"(?:rek\w*|nog\w*|kosc\w*|zebr\w*|nadgarst\w*|palc\w*|palec|obojczyk\w*|nos\w*|kostk\w*|biodr\w*|kolan\w*)"
# Matched on normalized text: lower case, no diacritics, "ł" -> "l".
PATTERNS = {
    "serious_injury": (
        rf"\bbroke (?:my |a )?{BODY}|\bbroken {BODY}|\bfractur\w*|\btorn (?:ligament|tendon|acl|meniscus)|"
        r"\b(?:ligament|tendon|acl) (?:tear|rupture)|\bdislocat\w*|\bconcussion|"
        rf"\bzlama\w* (?:\w+ )?{PL_BODY}|\b{PL_BODY} (?:\w+ )?zlaman\w*|"
        r"\bzerwan\w* (?:wiezadl\w*|sciegn\w*)|\bzwichn\w*|\bwstrzasnieni\w* mozgu"
    ),
    "feeling_very_unwell": (
        r"\b(?:feel|feeling|felt) (?:very|really|extremely|so) (?:sick|unwell|ill|bad)\b|"
        r"\bcan'?t keep (?:food|anything) down|\bvomiting|\bthrowing up|"
        r"\bblood in (?:my )?(?:urine|stool|vomit)|\bcoughing (?:up )?blood|\bhigh fever|"
        r"\bbardzo zle sie czuje|\bczuje sie bardzo zle|\bwymiotuj\w*|"
        r"\bkrew w (?:moczu|stolcu|wymiocinach)|\bwysok\w* goraczk\w*"
    ),
}
NEGATION = r"\b(?:no|not|without|never|don't|do not|didn't|nie|bez|brak)\b"
CONSULTATION = (
    "This sounds like something a doctor should look at. Please contact a doctor or physiotherapist "
    "before continuing your training or diet plan."
)


FLAG_MESSAGES = {
    "overtraining": (
        "Your recent health data shows signs of overtraining: your resting heart rate is rising together with worse "
        "sleep or more stress. Take it easier this week, rest and sleep more, and see a doctor if you feel unwell."
    ),
    "persistent_distress": (
        "In your recent check-ins you mentioned feeling low for a while. Consider talking with a doctor, "
        "psychologist or psychotherapist. You don't have to handle it alone."
    ),
    "self_harm_risk": (
        "In a recent check-in you mentioned thoughts of harming yourself. If they come back, call 112 or the support "
        "line 116 123, or reach out to someone you trust. You don't have to handle it alone."
    ),
}


def health_flags_notice(overtraining: bool, distress: set[str]) -> SafetyNotice | None:
    """A banner for the chat from the health flags (statistics and post-workout check-ins), not from the message."""
    codes = (["overtraining"] if overtraining else []) + sorted(distress)
    if "self_harm_risk" in codes and "persistent_distress" in codes:
        codes.remove("persistent_distress")  # the self-harm text already covers it
    if not codes:
        return None
    return SafetyNotice(level="consultation", codes=codes, message=" ".join(FLAG_MESSAGES[c] for c in codes))


def medical_notice(message: str) -> SafetyNotice | None:
    """A notice when the message needs a doctor; for "urgent" ones the agent should give no regular advice."""
    message = message.replace("ł", "l").replace("Ł", "L")  # NFKD doesn't strip the Polish "ł"
    notice = notice_for([o.model_dump() for o in literal_observations(message)])
    if notice is not None and notice.level == "urgent":
        return notice

    codes = [code for code, pattern in PATTERNS.items() if mentions(message, pattern)]
    if not codes:
        return notice
    if notice is None:
        return SafetyNotice(level="consultation", codes=codes, message=CONSULTATION)
    return notice.model_copy(update={"codes": sorted({*notice.codes, *codes})})


def mentions(message: str, pattern: str) -> bool:
    for clause in re.split(CLAUSE_BOUNDARY, message, flags=re.IGNORECASE):
        text = normalized(clause)
        match = re.search(pattern, text)
        # Unlike post-workout check-ins, past injuries count too: "I broke my leg yesterday" still needs a doctor.
        if match and not re.search(NEGATION, text[: match.start()][-45:]):
            return True
    return False

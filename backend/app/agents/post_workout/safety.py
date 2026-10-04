import re
import unicodedata

from app.schemas.post_workout import SafetyNotice, SafetyObservation

URGENT_CODES = {"chest_discomfort", "severe_breathlessness", "fainting", "self_harm_risk"}
PATTERNS = {
    "chest_discomfort": (
        r"chest (?:pain|pressure|tightness)|pain in (?:my |the )?chest|"
        r"bol(?:i)? (?:mnie )?(?:w )?klat(?:ce|ka)|ucisk (?:w )?klatce"
    ),
    "severe_breathlessness": r"(?:cannot|can't|cant) breathe|struggling to breathe|nie moge oddychac|dusze sie",
    "fainting": (
        r"(?:i |just )?(?:fainted|passed out)|(?:feel|feeling) (?:like |about to )?(?:faint|pass out)|"
        r"zemdlal[ae]m|mdleje"
    ),
    "self_harm_risk": (
        r"(?:want|going|plan|intend) to (?:kill|hurt) myself|"
        r"(?:thinking|thoughts) (?:about|of) (?:suicide|self.harm)|"
        r"chce (?:sie zabic|zrobic sobie krzywde)|mysli samobojcze"
    ),
    "worsening_pain": r"pain (?:is |keeps )?(?:getting worse|worsening)|bol (?:sie )?nasila|bol nie (?:mija|ustepuje)",
    "movement_limited": r"(?:cannot|can't|cant) (?:walk|put weight|move)|nie moge (?:chodzic|stanac|ruszac)",
}
CLAUSE_BOUNDARY = r"[.!?;,\n]|\b(?:but|however|and|ale|oraz)\b"
HISTORICAL = r"\b(?:yesterday|last year|used to|wczoraj|kiedys)\b"
OTHER_PERSON_OR_HYPOTHETICAL = r"\b(?:my friend|my mother|if i|hypothetical)\b"


def normalized(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(character)
    )


def negated_or_not_current(clause: str, start: int, end: int) -> bool:
    before, after = clause[:start], clause[end:]
    # Conservative literal fallback; free-text extraction handles richer language separately.
    negation = r"\b(?:no|not|without|never|deny|denies|don't|do not|didn't|nie|bez|brak)\b"
    if re.search(negation, before[-45:]):
        # 'not sure' is uncertainty, not a negation of the symptom.
        cleaned = re.sub(r"\bnot sure\b|\bnie wiem\b", "", before[-45:])
        if re.search(negation, cleaned):
            return True
    historical = re.search(HISTORICAL, clause) and not re.search(r"\b(?:now|still|currently|teraz|nadal)\b", clause)
    resolved = re.search(r"\b(?:gone|resolved|no longer|ustapil|minal)\b", after)
    if resolved and re.search(r"\b(?:not|never|nie)\b", after[: resolved.start()]):
        resolved = None
    return bool(historical or re.search(OTHER_PERSON_OR_HYPOTHETICAL, before) or resolved)


def literal_observations(message: str) -> list[SafetyObservation]:
    result = []
    for clause in re.split(CLAUSE_BOUNDARY, message, flags=re.IGNORECASE):
        text = normalized(clause)
        for code, pattern in PATTERNS.items():
            match = re.search(pattern, text)
            if match and not negated_or_not_current(text, match.start(), match.end()):
                result.append(SafetyObservation(code=code, evidence=clause.strip()))
    return result


def verified_observations(message: str, observations: list[SafetyObservation]) -> list[SafetyObservation]:
    result = []
    for observation in observations:
        evidence = normalized(observation.evidence)
        if evidence not in normalized(message):
            continue
        # Check the surrounding clause as well: a cropped quote must not hide "no chest pain".
        for clause in re.split(CLAUSE_BOUNDARY, message, flags=re.IGNORECASE):
            clause = normalized(clause)
            start = clause.find(evidence)
            if start < 0 or negated_or_not_current(clause, start, start + len(evidence)):
                continue
            if re.search(r"\b(?:no |not |without |never |don't |do not |nie |brak |if i |my friend )", evidence):
                continue
            result.append(observation)
            break
    return result


def notice_for(observations: list[dict], pain_intensity: int | None = None) -> SafetyNotice | None:
    codes = sorted({item["code"] for item in observations})
    if any(code in URGENT_CODES for code in codes):
        if "self_harm_risk" in codes:
            message = (
                "Your wellbeing matters. Please reach out for urgent human support now. "
                "If you might harm yourself or cannot stay safe, contact local emergency services "
                "and ask someone you trust to stay with you. This chat cannot provide emergency care."
            )
        else:
            message = (
                "Please pause this check-in and seek urgent medical advice about the symptoms you described. "
                "If they are ongoing or severe, or you have chest discomfort with breathing difficulty "
                "or faintness, contact local emergency services now. This chat cannot assess the cause."
            )
        return SafetyNotice(level="urgent", codes=codes, message=message)
    physical = bool(set(codes) & {"worsening_pain", "movement_limited"}) or (
        pain_intensity is not None and pain_intensity >= 7
    )
    mental = "persistent_distress" in codes
    if not physical and not mental:
        return None
    messages = []
    if physical:
        messages.append(
            "You reported significant or concerning pain. Please consider contacting a doctor "
            "or physiotherapist, especially if it persists, worsens or limits movement."
        )
    if mental:
        messages.append(
            "If this distress is ongoing or affecting everyday life, consider talking with "
            "a doctor, psychologist or psychotherapist. You do not have to handle it alone."
        )
    return SafetyNotice(level="consultation", codes=codes or ["reported_high_pain"], message=" ".join(messages))

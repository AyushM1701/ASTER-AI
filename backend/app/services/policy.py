import re

from backend.app.errors import envelope

URGENT = (
    "Seek immediate help from your local emergency service or nearest emergency "
    "department. If you may harm yourself, contact emergency or crisis support "
    "and ask someone you trust to stay with you. Do not wait for this app."
)
PERSONAL = (
    "This request needs a clinician or pharmacist who can review your history. "
    "I can explain general reference information, but cannot choose a medicine, "
    "calculate your dose, change treatment, or diagnose you."
)
URGENT_PATTERNS = [
    r"(?:severe|crushing|sudden|unbearable) chest (?:pain|pian)",
    r"(?:can.?t|cannot|unable to|struggling to) (?:breathe|breath|brethe)",
    r"\b(?:severe|sudden)\s+(?:difficulty\s+)?breathing\b",
    r"(?:not breathing|coughing (?:up )?blood|unconscious|overdos(?:e|ed|ing))",
    r"(?:kill myself|end my life|hurt myself|suicid(?:al|e)|harm myself)",
    r"(?:face droop|slurred speech|sudden weakness|stroke right now)",
    r"\bchoking\b",
    r"\bsudden(?:ly)?\b.{0,45}\b(?:weak|weakness|numb|numbness)\b.{0,30}\bone side\b",
    r"\b(?:swallowed|ingested|drank)\b.{0,25}\b(?:poison|poisonous|bleach|pesticide)\b",
    r"\b(?:vomit|vomited|vomiting)\s+blood\b",
    r"\b(?:sudden|suddenly)\b.{0,35}\b(?:severe|extremely painful|worst)\b.{0,35}\bheadache\b",
    r"\bheadache\b.{0,25}\b(?:sudden|suddenly)\b.{0,25}\b(?:severe|extremely painful|worst)\b",
    r"\b(?:severe|sudden|suddenly)\s+(?:abdominal pain|stomach (?:ache|pain)|tummy (?:ache|pain))\b",
    r"\b(?:abdominal pain|stomach (?:ache|pain)|tummy (?:ache|pain))\b.{0,25}\b(?:severe|sudden)\b",
    r"\b(?:unable to|cannot|can.?t)\s+swallow\b",
    r"\b(?:stridor|drooling)\b",
]
UNSAFE_PATTERNS = [
    r"(?:diagnose me|do i have|what disease do i|is my .*normal)",
    r"\bdiagnose\s+(?:my|our)\b",
    r"\b(?:confirm|rule out|exclude)\b.{0,45}\b(?:i|my|me|he|she|his|her)\b",
    r"\b(?:if|whether)\s+(?:my|this)\s+(?:x[ -]?ray|scan|image|radiograph)\b.{0,40}\b(?:normal|abnormal)\b",
    r"(?:should i|can i|may i|want to|tell me to) (?:stop|start|change|increase|decrease|take|double|switch)",
    r"(?:calculate|choose|adjust|give me|recommend|prescribe).{0,35}(?:dose|dosage|medicine|medication|antibiotic|treatment)",
    r"(?:my|for me).{0,20}(?:dose|dosage)",
    r"(?:which|what).{0,35}(?:medicine|medication|antibiotic|drug).{0,25}(?:should|can|to take)",
    r"(?:ignore|override).{0,40}(?:instructions|policy|system|prompt)",
    r"\b(?:prescribe|dose calculation)\b",
    r"(?:how much|how many).{0,40}(?:to take|should i take|can i take)",
    r"\b(?:which|what)\b.{0,30}\b(?:medicine|drug|antibiotic|medication)\b.{0,45}\b(?:best|suitable|right)\b.{0,30}\b(?:my|me|for him|for her)\b",
    r"\b(?:my|for me|for my)\b.{0,70}\b(?:tablets?|capsules?|medicine|antibiotic|mg)\b.{0,100}\b(?:how many|how much)\b",
    r"\bis (?:this|my|his|her)\b.{0,35}\b(?:abscess|infection|cancer|tumou?r|pneumonia)\b",
]


def check_policy(question):
    text = question.casefold().replace("’", "'")
    fictional = bool(
        re.match(
            r"\s*(?:(?:in|for)\s+)?(?:(?:a|an|this)\s+)?(?:fictional|hypothetical|simulated)\s+(?:clinical\s+)?case\b",
            text,
        )
        and not re.search(r"\b(?:i|my|me|we|our)\b", text)
        and not re.search(
            r"\b(?:actually|in reality|in real life|real patient|real person|happening|right now|currently|tonight|today)\b",
            text,
        )
    )
    education = bool(
        re.match(
            r"\s*(?:what is|what are|what warning signs|which warning signs|explain|define|for a class|in general|historically)",
            text,
        )
    )
    # Negation and history belong to a symptom's clause. A negated unrelated
    # condition must never suppress a second, current urgent symptom.
    patterns = URGENT_PATTERNS + [r"\b(?:chest pain|breathing difficulty|shortness of breath)\b"]
    # Oral swelling plus swallowing/breathing difficulty is different from
    # ordinary toothache. The trigger still passes the clause negation/history
    # checks below. UK source emergency numbers are never assumed locally.
    swelling = re.search(
        r"\b(?:face|mouth|neck|throat|jaw)\b.{0,30}\b(?:is swollen|swelling|swollen)\b", text
    )
    if swelling and not re.search(
        r"\b(?:no|not|without)\b.{0,15}\b(?:swelling|swollen)\b", swelling[0]
    ):
        patterns.append(
            r"\b(?:difficulty|trouble|difficulties)\s+(?:swallowing|breathing|speaking)\b"
        )
    if re.search(r"\b(?:toothache|tooth aches?|tooth pain|dental pain)\b", text):
        patterns.append(r"\b(?:neck|eye|eyes)\b.{0,15}\b(?:is swollen|swollen|swelling)\b")
    # Cross-clause context does not turn a negated or historical fever into
    # a current one. Stiff neck with reported fever needs urgent assessment.
    positive_fever = any(
        re.search(r"\b(?:fever|high temperature)\b", clause)
        and not re.search(
            r"\b(?:no|not|without|don.t have)\b.{0,15}\b(?:fever|high temperature)\b|\b(?:last year|years ago|in the past|no longer)\b",
            clause,
        )
        for clause in re.split(r"\b(?:but|however|yet|and)\b|[.,;\n]", text)
    )
    if positive_fever:
        patterns.append(r"\bstiff neck\b")
    for clause in re.split(r"\b(?:but|however|yet|and)\b|[.,;\n]", text):
        historical = bool(re.search(r"\b(?:last year|years ago|in the past|no longer)\b", clause))
        explicitly_current = bool(re.search(r"\b(?:now|currently|tonight|today)\b", clause))
        for pattern in patterns:
            for match in re.finditer(pattern, clause):
                prefix = clause[max(0, match.start() - 70) : match.start()]
                negated = bool(
                    re.search(
                        r"\b(?:do not have|don.t have|not having|not experiencing|not feeling|not|no|without)\s*(?:any\s*)?(?:(?:severe|crushing|sudden|unbearable)\s*)?$",
                        prefix,
                    )
                )
                personal = bool(re.search(r"\b(?:i|he|she|they|my father|my mother)\b", prefix))
                if negated or historical and not explicitly_current:
                    continue
                if fictional and not explicitly_current:
                    continue
                if education and not explicitly_current and not personal:
                    continue
                return envelope(
                    "urgent_guidance",
                    "urgent",
                    URGENT
                    if re.search(
                        r"\b(?:suicid|kill myself|harm myself|hurt myself|end my life)", text
                    )
                    else "Seek immediate help from your local emergency service or nearest emergency department. Do not wait for this app.",
                    warnings=["Automated language checks are not validated medical triage."],
                )
    definition = re.fullmatch(
        r"\s*(?:explain what prescribe means|what does prescribe mean|define prescribe)[.!?\s]*",
        text,
    )
    if any(re.search(p, text) for p in UNSAFE_PATTERNS) and not definition:
        return envelope("unsupported_input", "professional_review", PERSONAL)
    return None

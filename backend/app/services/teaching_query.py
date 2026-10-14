"""Separate presentation requests from medical meaning without rewriting facts."""

import re
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class TeachingQuery:
    focus: str
    requests: tuple[str, ...] = ()


# Exact academic headings only: an arbitrary 'For ...' prefix can contain a
# patient population, disease or experimental setting that must be retained.
ACADEMIC_HEADINGS = frozenset({
    "", "viva", "exam", "student", "anatomy", "physiology", "biochemistry",
    "pathology", "pharmacology", "microbiology", "community medicine",
    "general medicine", "general surgery", "paediatrics", "psychiatry",
    "obstetrics and gynaecology", "ophthalmology", "orthopaedics",
    "otorhinolaryngology", "radiodiagnosis", "anaesthesiology",
    "forensic medicine and toxicology", "dermatology venereology and leprosy",
    "biostatistics and research methodology", "oral and dental pathology",
    "applied gross anatomy of head and neck histology and genetics",
    "basic histo techniques and microscopy", "physiology general oral",
    "recent molecular techniques", "cell biology", "general histology",
    "general pathology", "general microbiology", "basic immunology",
    "systemic microbiology applied microbiology",
    "oral biology oral and dental histology", "iii mds",
})


def strip_academic_prefix(text):
    prefix = re.match(r"^For\s+(?:(?:a|an)\s+)?((?:MBBS|MDS)\b[^,]{0,180}|viva|exam),?\s+(?=(?:explain|describe|discuss|define)\b)", text, re.I)
    if not prefix:
        return text
    heading = re.sub(r"^(?:MBBS|MDS)\b", "", prefix[1], flags=re.I)
    heading = " ".join(re.findall(r"[a-z]+", heading.casefold()))
    return text[prefix.end():] if heading in ACADEMIC_HEADINGS else text


@lru_cache(maxsize=16384)
def plan_question(question):
    text = question.strip()
    requests = []
    text = strip_academic_prefix(text)
    mcq = re.match(r"^([^:!?]{1,100}):\s*[A-D][.)]?\s+.+?;\s*[A-D][.)]?\s+", text, re.I)
    if mcq:
        text = mcq[1]
        requests.append("Multiple-choice analysis and a correct-choice verdict")
    elif re.match(r"^(?:(?:in|for)\s+)?(?:a\s+)?(?:fictional|hypothetical|simulated)\s+(?:\w+\s+){0,3}case\b", text, re.I):
        instruction = re.search(r"[.!?]\s+((?:explain|describe|discuss|define)\b.*)$", text, re.I)
        if instruction:
            text = instruction[1]
            requests.append("Interpretation and reasoning for the preceding fictional case")
    # These are explicit answer tasks, not arbitrary trailing clinical clauses.
    instructions = re.compile(
        r"^(?:address (?:the stated curriculum scope|the underlying mechanism)|"
        r"identify common misconceptions|state what cannot be established|"
        r"explain the reasoning, distinguishing features and limitations)\b", re.I)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    kept = []
    for sentence in sentences:
        if instructions.match(sentence):
            requests.append(sentence.rstrip(".!?"))
        else:
            kept.append(sentence)
    text = " ".join(kept)
    applied = re.fullmatch(r"Apply\s+(.+?)\s+to a fictional educational example(?:\s+relevant to\s+.+)?[.!?]?", text, re.I)
    if applied:
        text = applied[1]
        requests.append("A fictional applied example and its reasoning")
    text = re.sub(r"^Give (?:an?\s+)?(?:analytical\s+)?(?:viva\s+)?discussion of\s*:?\s*", "Explain ", text, flags=re.I)
    text = re.sub(r"^(?:please\s+)?(?:(?:can|could|would) you\s+)?(?:please\s+)?", "", text, flags=re.I)
    text = re.sub(r"\s+(?:in|using)\s+(?:simple terms|plain language|simple words)(?:\s+for a patient)?(?=[.!?]?$)", "", text, flags=re.I)
    text = re.sub(r"\s+(?:for (?:a|an)\s+(?:MBBS\s+|MDS\s+)?(?:viva|exam)|in detail)(?=[.!?]?$)", "", text, flags=re.I)
    # Never strip a context qualifier, negation, a second medical question or a
    # real symptom. The original input is separately retained by the caller.
    text = re.sub(r"^(?:explain|describe|discuss|define|what (?:is|are)|tell me about)\s*:?\s*", "", text, flags=re.I)
    return TeachingQuery(text.strip(" .!?:"), tuple(requests))

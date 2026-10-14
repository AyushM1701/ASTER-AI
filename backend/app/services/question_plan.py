"""Bounded deterministic task planning. Clinical context is never discarded."""

import json
import re
from functools import lru_cache
from typing import Literal

from pydantic import Field

from backend.app.schemas import StrictModel


class RequestedFacet(StrictModel):
    topic_id: str
    facet: str
    query: str
    scope: str = ""
    requested_by_user: bool = True


class QuestionPlan(StrictModel):
    version: Literal["2"] = "2"
    original_question: str
    audience: Literal["understand", "study", "research"] = "understand"
    task: str = "explain"
    topic: str
    subquestions: list[str] = Field(default_factory=list)
    qualifiers: list[str] = Field(default_factory=list)
    depth: str = "simple_then_deeper"
    medical_audience: Literal["patient", "student", "research"] = "patient"
    intent: Literal[
        "symptom_information",
        "concept_explanation",
        "mechanism",
        "comparison",
        "practice",
        "research_assistance",
    ] = "concept_explanation"
    primary_subject: str = ""
    requested_information: list[str] = Field(default_factory=list)
    patient_context: dict[str, str | bool] = Field(default_factory=dict)
    safety_qualifiers: list[str] = Field(default_factory=list)
    individualized_advice_requested: bool = False
    required_response_elements: list[str] = Field(default_factory=list)
    canonical_topics: list[str] = Field(default_factory=list)
    primary_topic_id: str | None = None
    facets: list[RequestedFacet] = Field(default_factory=list)
    comparison_axes: list[str] = Field(default_factory=list)
    marks: int | None = Field(None, ge=1, le=100)
    is_fictional_case: bool = False
    needs_clarification: bool = False
    context_topic: str | None = None


SYMPTOMS = {
    "toothache": r"\b(?:toothaches?|dental pain|tooth pain|pain when biting|pain on biting)\b|\b(?:tooth|teeth|gums?)\b.{0,65}\b(?:aches?|aching|hurts?|hurt|pain|throbbing|sensitive)\b|\b(?:pain|aches?|aching|hurt)\b.{0,35}\b(?:tooth|teeth)\b",
    "headache": r"\b(?:headaches?|head aches?|head pain)\b|\bhead\b.{0,20}\b(?:hurts?|hurt)\b",
    "fever": r"\b(?:fevers?|high temperature)\b",
    "sore_throat": r"\b(?:sore throat|throat pain|painful throat)\b|\bthroat\b.{0,20}\b(?:hurts?|hurt|sore)\b",
    "abdominal_pain": r"\b(?:abdominal pain|stomach aches?|stomach pain|tummy aches?|belly pain)\b|\b(?:stomach|tummy|abdomen|belly)\b.{0,20}\b(?:hurts?|hurt|pain)\b",
}
SYMPTOM_ELEMENTS = [
    "meaning",
    "possible_causes",
    "uncertainty",
    "professional_followup",
    "warning_signs",
]


def understand_question(question, audience, task):
    """Resolve operations, not diagnoses. Context contains only explicit text."""
    technical = bool(
        re.search(
            r"\b(?:mechanisms?|pathogenesis|pathophysiology|histology|embryology|BMPs?|periodontal ligament|odontogenic|erupt(?:ion)?|development|signalling|signaling|viva|MCQ|MDS|MBBS)\b",
            question,
            re.I,
        )
    )
    subjects = [key for key, pattern in SYMPTOMS.items() if re.search(pattern, question, re.I)]
    subject = subjects[0] if subjects else ""
    personal = bool(re.search(r"\b(?:my|i have|i am|i'm|my child|my baby)\b", question, re.I))
    symptom = bool(
        subject
        and (
            personal
            or not technical
            and task not in {"compare", "viva", "quiz", "revise", "mechanism"}
        )
    )
    # Unmapped symptom requests fail closed rather than becoming general chat.
    if (
        not subject
        and not technical
        and re.search(
            r"\b(?:why does .+ (?:hurt|ache)|why do .+ (?:hurt|ache)|what does it mean if .+ (?:hurts?|aches?)|what could .+ pain mean|what causes .+ pain|my .+ hurts?|my .+ aches?)\b",
            question,
            re.I,
        )
    ):
        subject, symptom = "unmapped_symptom", True
    medical_audience = (
        "research"
        if audience == "research"
        else "patient"
        if symptom
        else "student"
        if technical or audience == "study" or task != "explain"
        else "patient"
    )
    intent = (
        "symptom_information"
        if symptom
        else {
            "compare": "comparison",
            "mechanism": "mechanism",
            "viva": "practice",
            "quiz": "practice",
            "revise": "practice",
        }.get(task, "research_assistance" if audience == "research" else "concept_explanation")
    )
    context = {}
    if symptom and len(subjects) > 1:
        context["cooccurring_symptoms"] = ", ".join(subjects)
    if symptom and personal and technical:
        context["additional_technical_detail"] = True
    if personal:
        context["explicit_statement"] = question
    age = re.search(
        r"\b(\d+)\s*(?:-|\s)?(?:years?|months?|weeks?)\s*(?:-|\s)?old\b", question, re.I
    )
    if age:
        context["age_statement"] = age[0]
    if re.search(r"\b(?:child|baby|infant|toddler)\b", question, re.I):
        context["population"] = "child"
    elif re.search(r"\b(?:adult|adults)\b", question, re.I):
        context["population"] = "adult"
    if re.search(r"\b(?:i am|i'm|my wife is)\s+pregnant\b|\bduring pregnancy\b", question, re.I):
        context["pregnancy"] = True
    for name in (
        "renal impairment",
        "liver disease",
        "chemotherapy",
        "diabetes",
        "weakened immune system",
    ):
        if re.search(r"\b(?:with|have|has|on|during)\s+" + name + r"\b", question, re.I):
            context[name] = True
    qualifiers = []
    for name, pattern in (
        ("cold_trigger", r"\bcold\b"),
        ("biting_pain", r"\bbiting|\bbite\b"),
        ("gum_cause", r"\bgum(?:s| problems| disease)?\b"),
    ):
        if subject == "toothache" and re.search(pattern, question, re.I):
            qualifiers.append(name)
    safety = [
        m[0]
        for m in re.finditer(
            r"\b(?:swollen|swelling|difficulty swallowing|difficulty breathing|sudden|severe|fever|stiff neck|vomiting blood)\b",
            question,
            re.I,
        )
    ]
    individualized = bool(
        re.search(
            r"\b(?:diagnose me|do i have|definitely mean|which antibiotic|what dose|should i take|prescribe|treat my)\b",
            question,
            re.I,
        )
    )
    required = [*SYMPTOM_ELEMENTS, *("specific_context" for _ in qualifiers[:1])] if symptom else []
    return dict(
        medical_audience=medical_audience,
        intent=intent,
        primary_subject=subject,
        requested_information=qualifiers,
        patient_context=context,
        safety_qualifiers=safety,
        individualized_advice_requested=individualized,
        required_response_elements=required,
    )


def plan_question(question, audience="understand", context_topic=None):
    task = "explain"
    for name, pattern in (
        ("compare", r"^(?:compare\b|what is the difference between\b|differences between\b)"),
        ("viva", r"\bviva(?: question| on| about|$)"),
        ("quiz", r"^(?:quiz me|test my understanding)\b"),
        ("revise", r"^how do i revise\b"),
        ("mechanism", r"\b(?:mechanism|how does .+ work)\b"),
        ("review_answer", r"^review my answer\b"),
        ("fictional_case", r"^(?:apply|practise) .+ (?:to|with|in) a fictional case\b"),
    ):
        if re.search(pattern, question, re.I):
            task = name
            break
    if re.search(r"\b(?:viva|act as (?:an? )?MDS .+ examiner)\b", question, re.I):
        task = "viva"
    topic = re.sub(
        r"^(?:give|ask) me (?:a )?viva question (?:on|about)\s+|^(?:start (?:a )?)?viva (?:on|about)\s+|^quiz me on\s+|^how do i revise\s+",
        "",
        question,
        flags=re.I,
    ).strip(" .?!")
    if task == "viva":
        target = re.search(r"\b(?:viva(?: question)?\s+(?:on|about)|questions?\s+(?:on|about))\s+(.+)", question, re.I)
        if target:
            topic = re.split(r"[.!?;]|,\s*(?:wait|evaluate|assess|grade|one at a time)|\s+and\s+(?:wait|evaluate|assess|grade)\b", target[1], maxsplit=1, flags=re.I)[0].strip(" .?!")
        else:
            case_target = re.search(r"\bpresent\s+(?:(?:a|an)\s+)?(?:fictional\s+)?(?:patient|case)[^.!?]*?\b(?:with|on|about)\s+(?:a\s+)?(.+?)(?:,|[.!?]|$)", question, re.I)
            if case_target:
                topic = case_target[1].strip(" .?!")
            else:
                findings_target = re.search(r"\bpresent\s+(?:the\s+)?(?:written\s+)?(?:radiographic|clinical|histopathological) findings of\s+(.+?)(?:[.!?]|$)", question, re.I)
                study_target = re.search(r"\bpresent\s+(?:a\s+)?(?:fictional\s+)?([\w-]+ study)\b", question, re.I)
                if findings_target or study_target:
                    topic = (findings_target or study_target)[1]
    qualifiers = re.findall(
        r"\b(?:in|during|for|with)\s+(?:pregnancy|children|a child|infants|adults|renal impairment|liver disease)\b",
        question,
        re.I,
    )
    parts = re.split(
        r"\s*(?:;|\?\s+(?=(?:what|why|how|can|does)\b)|\s+and\s+(?=(?:what|why|how)\b))\s*",
        question,
        flags=re.I,
    )
    if len(parts) > 4:
        parts = [question]
    prefix = re.match(
        r"^(explain|define|what is|what are|tell me about)\s+(.+)$", question.strip(" .?!"), re.I
    )
    # A joined anatomical name or population-qualified phrase is kept intact.
    if (
        prefix
        and not qualifiers
        and not re.search(
            r"\b(?:head and neck|antigen and antibody|blood and blood grouping|for|during|with|in)\b",
            prefix[2],
            re.I,
        )
    ):
        subjects = re.split(r"\s+and\s+", prefix[2], flags=re.I)
        if 1 < len(subjects) <= 4:
            parts = [prefix[1] + " " + subject for subject in subjects]
    plan = QuestionPlan(
        original_question=question,
        audience=audience,
        task=task,
        topic=topic,
        subquestions=parts,
        qualifiers=qualifiers,
        **understand_question(question, audience, task),
    )
    return hierarchical_plan(plan, context_topic)


FACET_PATTERNS = {
    "definition": r"\b(?:define|definition|what (?:is|are))\b",
    "classification": r"\b(?:classify|classification|classifications)\b",
    "layers": r"\blayers?\b",
    "functions": r"\bfunctions?\b",
    "structure": r"\b(?:structure|architecture)\b",
    "anatomical_examples": r"\b(?:anatomical examples?|examples?|anatomic sites?|locations?|sites)\b",
    "clinical_features": r"\b(?:clinical(?!\s+(?:significance|implications?|relevance)\b)(?: features?| presentation| behavior| behaviour)?|presentation|symptoms?)\b",
    "clinical_significance": r"\bclinical (?:significance|implications?|relevance)\b",
    "radiographic_features": r"\b(?:radiographic|radiological|radiology|imaging)\b",
    "histopathology": r"\b(?:histolog\w*|histopatholog\w*|microscopic|morpholog\w*)\b",
    "intrinsic_pathway": r"\bintrinsic\b",
    "extrinsic_pathway": r"\bextrinsic\b",
    "molecular_features": r"\bmolecular\b",
    "stages": r"\b(?:stages?|sequence|chronology)\b",
    "epithelial_mesenchymal_interactions": r"\bepithelial[\s–—-]+mesenchymal(?:\s+interactions?)?\b|\breciprocal induction\b",
    "relationship_to_dysplasia": r"\b(?:relationship|relation|associated)\b[^.!?]{0,50}\bdysplasia\b",
    "architectural_features": r"\barchitectural\b",
    "cytological_features": r"\bcytolog\w*\b",
    "grading_limitations": r"\bgrading\b",
    "differential_diagnosis": r"\bdifferential\w*\b",
    "investigations": r"\b(?:investigations?|biopsy rationale|diagnostic methods?)\b",
    "mechanism": r"\b(?:mechanisms?|pathogenesis|etiopathogenesis|pathophysiology|biological basis|how does .+ work)\b",
    "cellular_features": r"\bcellular\b",
    "membrane_changes": r"\bmembrane\b",
    "nuclear_changes": r"\bnuclear\b",
    "inflammation": r"\binflammat\w*(?:\s+responses?)?\b",
    "outcome": r"\boutcomes?\b",
    "diagnostic_limitations": r"\b(?:diagnostic limitations?|limitations? of (?:clinical|diagnostic)|limitations? of (?:the )?evidence)\b",
    "biological_behavior": r"\bbiological behaviou?r\b",
    "invasion": r"\b(?:invasion|invasive patterns?)\b",
    "materials": r"\b(?:materials?|material properties)\b",
    "clinical_tests": r"\b(?:clinical examination|(?:clinical|diagnostic|sensibility|pulp|relevant|confirmatory) tests?|sensibility testing|relevant testing)\b",
    "management": r"\b(?:management(?: principles?)?|treatment (?:options?|approaches?|alternatives?|selection)|principles of (?:definitive )?management)\b",
}


def _comparison_subjects(text):
    """Read explicit comparison nouns, including provisional multi-entity lists."""
    match = re.search(r"\b(?:compare|differentiate(?:\s+between)?|differences? between)\s+(.+)", text, re.I)
    if not match:
        match = re.match(r"(.+?\s+(?:versus|vs\.?)\s+.+)", text, re.I)
    if not match:
        return []
    nouns = re.split(r"[.:?;]|(?:,\s*|\s+)(?:including|covering|emphasizing|emphasising)\b|\s+(?:in terms of|with respect to|with (?:anatomical )?examples?|along|based on|using|on the basis of|in|for|during|under)\b\s*", match[1], maxsplit=1, flags=re.I)[0]
    parts = re.split(r"\s*(?:,\s*(?:and\s+)?|\s+(?:and|versus|vs\.?|with|from)\s+)\s*", nouns, flags=re.I)
    # Parallel numbered subtypes share a name and terminal noun, e.g.
    # "Le Fort I, II and III fractures"; expand only explicit subtype tokens.
    first = re.fullmatch(r"(.+?)\s+([IVX]+|\d+)", parts[0].strip(), re.I) if parts else None
    last = re.fullmatch(r"([IVX]+|\d+)\s+(.+)", parts[-1].strip(), re.I) if parts else None
    if first and last and all(re.fullmatch(r"[IVX]+|\d+", part.strip(), re.I) for part in parts[1:-1]):
        parts = [f"{first[1]} {token} {last[2]}" for token in [first[2], *[part.strip() for part in parts[1:-1]], last[1]]]
    parts = _inherit_coordinated_noun(parts)
    if len(parts) > 2 and any(re.fullmatch(pattern, parts[-1], re.I) for pattern in FACET_PATTERNS.values()):
        parts.pop()
    names = [_subject_phrase(part, comparison=True) for part in parts if part.strip()]
    return names if 2 <= len(names) <= 6 and all(names) else []


def _inherit_coordinated_noun(parts):
    """Expand explicit adjectival coordination; never infer a disease identity."""
    from backend.app.services.mds_curriculum import TOPICS, aliases

    modifier = r"(?:non[ -]?)?(?:keratini[sz]ed|calcified|mineralized|vital|vitalised|vitalized|fixed|removable|acute|chronic|benign|malignant)"
    if len(parts) < 2 or not all(re.fullmatch(modifier, part.strip(), re.I) for part in parts[:-1]):
        return parts
    nouns = sorted({name for identity in TOPICS for name in aliases(identity)} | set(_editorial_nouns()), key=len, reverse=True)
    for noun in nouns:
        match = re.search(r"\s+(" + re.escape(noun) + r")$", parts[-1].strip(), re.I)
        if match and re.fullmatch(modifier, parts[-1].strip()[:match.start()], re.I):
            return [part.strip() + " " + match[1] for part in parts[:-1]] + [parts[-1]]
    return parts


def _operation_clauses(text):
    """Split requests at action boundaries, never at ordinary noun conjunctions."""
    action = r"(?:define|explain|discuss|describe|classify|enumerate|compare|differentiate|design|evaluate|what|why|how)\b"
    return [part.strip(" ,") for part in re.split(
        r";|[.!?]\s+(?=" + action + r")|,\s*(?:and\s+)?(?=" + action + r")|\s+and\s+(?=" + action + r")",
        text, flags=re.I,
    ) if part.strip(" ,")]


def _pedagogic_scope(text):
    """Output instructions do not constrain the clinical source population."""
    if re.search(r"\b(?:adults?|children|patients?|recipients?|diabet\w*|pregnan\w*|renal impairment|liver disease|(?:primary|permanent|deciduous) teeth)\b", text, re.I):
        return False
    if re.match(r"(?:in terms of|with respect to|in (?:a |the )?(?:table|structured table))\b", text, re.I):
        return True
    return bool(re.search(
        r"\b(?:each (?:cell|row|column)|teaching context|educational context|"
        r"postgraduate|revision|viva|exam|student|MDS|MBBS|simple (?:terms|language)|plain language|detail|"
        r"anatomical examples?|examples?|marks?|histolog\w*|radiographic|clinical features|"
        r"definition|functions?|layers?)\b", text, re.I,
    ))


@lru_cache(maxsize=1)
def _editorial_nouns():
    """Lexical boundaries only; an editorial title establishes no readiness."""
    from backend.app.paths import install_root

    try:
        document = json.loads((install_root() / "configs/all_mds_topics.json").read_text(encoding="utf-8"))
        names = {topic["title"] for specialty in document["specialties"] for topic in specialty["topics"] if isinstance(topic.get("title"), str)}
        return tuple(sorted(names, key=len, reverse=True))
    except (OSError, ValueError, KeyError, TypeError):
        return ()


def _facet_suffix_only(text):
    recognized = any(re.search(pattern, text, re.I) for pattern in FACET_PATTERNS.values())
    for pattern in FACET_PATTERNS.values():
        text = re.sub(pattern, "", text, flags=re.I)
    text = re.sub(r"\b(?:and|features?|criteria|pathways?|changes?|the|its|their)\b|[,\s–—-]", "", text, flags=re.I)
    return recognized and not text


def _subject_phrase(text, comparison=False):
    """Extract a bounded explicit noun phrase without assigning medical identity."""
    from backend.app.services.mds_curriculum import aliases, resolve_topics

    text = re.split(r"[.!?:;]|(?:,\s*|\s+)(?:including|covering|emphasizing|emphasising|discussing)\b", text, maxsplit=1, flags=re.I)[0].strip()
    preserve_noun = comparison
    if not comparison:
        essay = re.match(r"^(?:write|give|prepare)\s+(?:(?:an?|the)\s+)?(?:\d+[ -]marks?\s+)?(?:educational\s+)?(?:essay|short note|long answer)\s+(?:on|about)\s+(.+)$", text, re.I)
        if essay:
            text, preserve_noun = essay[1], True
        else:
            prefix = re.match(r"^(?:critically\s+)?(appraise|review|evaluate|design|explain|describe|discuss|define|classify|enumerate|what is|what are)\s+(.+)$", text, re.I)
            if not prefix:
                return ""
            text = prefix[2]
            preserve_noun = prefix[1].casefold() in {"define", "what is", "what are", "appraise", "review", "evaluate", "design"}
            causal_subject = re.match(r"^how\s+(.+?)\s+(?:influence|influences|affect|affects|contribute|contributes|regulate|regulates|respond|responds|cause|causes)\b", text, re.I)
            if causal_subject:
                text, preserve_noun = causal_subject[1], True
            target = re.match(r"^(?:the\s+)?(?:mechanisms?|pathogenesis|etiopathogenesis|pathophysiology|histopatholog\w* (?:features?|findings)|histolog\w* (?:features?|findings)|architectural features?|cytological features?)\s+of\s+(.+)$", text, re.I)
            if target:
                text, preserve_noun = target[1], True
            else:
                operation_head = re.match(r"^(?:the\s+)?(.+?)\s+(?:of|associated\s+with|related\s+to)\s+(.+)$", text, re.I)
                if operation_head and _facet_suffix_only(operation_head[1]):
                    text, preserve_noun = operation_head[2], True
                elif operation_head and re.fullmatch(
                    r"(?:(?:normal|molecular|biological|clinical|surgical|principal|modern)\s+)?(?:principles?|basis|chronology|stages?|anatomy|histology|structure|functions?|classification|histopathological features)(?:\s+and\s+(?:functions?|histology|histopathological features))?",
                    operation_head[1], re.I,
                ):
                    text, preserve_noun = operation_head[2], True
                elif operation_head and re.fullmatch(r"(?:molecular|cellular)\s+(?:pathogenesis|mechanisms?)", operation_head[1], re.I):
                    text, preserve_noun = operation_head[2], True
    # Coordinated requests for a recognized facet must not extend the noun.
    # Unknown role descriptions remain intact rather than guessing an entity.
    role = re.search(r"\s+and\s+(?:the\s+)?role\s+of\s+(.+)$", text, re.I)
    if role and _facet_suffix_only(role[1]):
        text = text[:role.start()]
    text = re.split(r"\s+(?:along|by|based on|according to|as (?:an?|the)|in|for|during|under|with|following|after|before)\s+|\s+at\s+(?:the\s+)?(?=(?:cellular|tissue|molecular)\b)", text, maxsplit=1, flags=re.I)[0]
    # A known noun phrase can be followed directly by requested facets, e.g.
    # "dentigerous cyst histology". Only remove a suffix composed entirely of
    # facet grammar; an unknown modifier still keeps the longer entity intact.
    for identity in resolve_topics(text):
        for alias in sorted(aliases(identity), key=len, reverse=True):
            match = re.match(re.escape(alias) + r"\s+(.+)$", text, re.I)
            if not match:
                continue
            if _facet_suffix_only(match[1]):
                text = text[:match.start(1)].strip()
                break
    for noun in _editorial_nouns():
        noun_pattern = re.escape(noun).replace(r"\ ", r"[\s–—-]+")
        match = re.match(noun_pattern + r"\s+(.+)$", text, re.I)
        if match and _facet_suffix_only(match[1]):
            text = text[:match.start(1)].strip()
            break
    if not preserve_noun:
        matches = [match for name, pattern in FACET_PATTERNS.items() if name != "definition" and not (name == "classification" and re.search(r"['’]s\s+classification\b", text, re.I)) for match in [re.search(pattern, text, re.I)] if match and match.start() > 0]
        if matches:
            text = text[:min(match.start() for match in matches)]
    text = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.I).strip(" ,;-?!")
    if not text or len(text.split()) > 8 or re.search(r"\b(?:its|their|that|these|my|your|answer|essay)\b", text, re.I) or not preserve_noun and re.search(r"\band\b", text, re.I) or not comparison and re.search(r"\bi\b", text, re.I):
        return ""
    return text


def _subject_identity(subject):
    from backend.app.services.mds_curriculum import aliases, resolve_topics

    normalized = re.sub(r"[\s–—-]+", " ", subject.casefold()).strip()
    for identity in resolve_topics(subject):
        if any(re.sub(r"[\s–—-]+", " ", alias.casefold()).strip() == normalized for alias in aliases(identity)):
            return identity
    # A longer explicit entity is provisional, not the shorter known entity
    # it happens to contain (e.g. a disorder named after a normal process).
    return "local:" + "_".join(re.findall(r"\w+", subject.casefold()))


def _requested_facets(text):
    facets = [name for name, pattern in FACET_PATTERNS.items() if re.search(pattern, text, re.I)]
    if re.search(r"\barchitecture\b", text, re.I):
        histology_context = bool(re.search(r"\b(?:histolog\w*|histopatholog\w*|cytolog\w*|microscopic)\b", text, re.I))
        facet = "architectural_features" if histology_context else "structure"
        if histology_context and not re.search(r"\bstructure\b", text, re.I):
            facets = [name for name in facets if name != "structure"]
        if facet not in facets:
            facets.append(facet)
    facets.extend(detail for detail in _explicit_requested_details(text) if detail not in facets)
    return facets


def _explicit_requested_details(text):
    """Keep bounded user-named subparts; these names never supply answer content."""
    details = []
    for match in re.finditer(r"\b(?:including|emphasizing|emphasising|covering)\s+([^.!?;]+)", text, re.I):
        tail = re.split(
            r"\s+(?:without|answer|provide|wait|evaluate|assess|grade)\b|"
            r"\s+(?:in|for|during|under|with)\s+(?:simple|plain|postgraduate|educational|a teaching|children|adults|primary teeth|permanent teeth)\b",
            match[1], maxsplit=1, flags=re.I,
        )[0]
        for part in re.split(r"\s*(?:,\s*(?:and\s+)?|\s+and\s+)\s*", tail, flags=re.I):
            part = re.sub(r"^(?:the\s+)?(?:roles?|contributions?|importance)\s+of\s+", "", part, flags=re.I)
            part = re.sub(r"^(?:the|a|an|its|their|relevant)\s+", "", part, flags=re.I).strip(" ,:-")
            if not part or len(part) > 160 or len(part.split()) > 12 or re.search(r"\b(?:ask|wait|evaluate|assess|grade|answer|prescribe|diagnose|my|your|should)\b", part, re.I):
                continue
            # Existing facet grammar remains canonical. Retain a named detail
            # when substantive words remain (e.g. "inflammatory mediators"
            # needs more than an arbitrary inflammation excerpt).
            remainder = part
            for pattern in FACET_PATTERNS.values():
                remainder = re.sub(pattern, "", remainder, flags=re.I)
            remainder = re.sub(r"\b(?:the|a|an|and|of|its|their|roles?|features?|findings|principles?|changes?|levels?|pathways?|criteria|steps?|characteristics|diagnostic)\b|[^\w]", "", remainder, flags=re.I)
            if remainder:
                name = "_".join(re.findall(r"\w+", part.casefold()))
                if name and name not in details:
                    details.append(name)
    return details


def hierarchical_plan(plan, context_topic):
    """Preserve old API fields while giving each retrieval facet its subject."""
    from backend.app.services.mds_curriculum import resolve_topics, topic_name

    original = plan.original_question
    question = plan.topic if plan.task == "viva" else original
    question = re.sub(r"^\s*now\s+(?=(?:explain|describe|discuss|define|classify|compare|differentiate)\b)", "", question, flags=re.I)
    continuation = bool(re.match(r"\s*go deeper\b", question, re.I))
    if continuation:
        question = re.sub(r"^\s*go deeper(?:\s+into)?\s+", "Explain ", question, flags=re.I)
    personal = bool(re.search(r"\b(?:i|my|me|our|real patient|actually|in real life|today|tonight)\b", original, re.I))
    plan.is_fictional_case = bool(re.search(r"\b(?:fictional|hypothetical|simulated)\b[^.!?]*\b(?:case|patients?|child|educational example)\b", original, re.I)) and not personal
    # Educational operation grammar must never replace a patient's symptom
    # request or remove its original component questions.
    if plan.intent == "symptom_information" and not plan.is_fictional_case:
        return plan
    unresolved = bool(re.search(r"\b(?:its|their|that|these|both conditions|each stage|each measure)\b|\b(?:compare|differentiate)\s+it\b", question, re.I))
    if context_topic and unresolved and not _subject_phrase(question):
        question = re.sub(r"\b(?:it|its|their|that|these)\b", context_topic, question, flags=re.I)
        plan.context_topic = context_topic
    compare = plan.task != "viva" and bool(re.search(r"\b(?:compare|differentiate|comparison|differences? between|versus|vs\.?)\b", question, re.I))
    if compare and re.search(r"\boral,\s*sulcular\b", question, re.I):
        question = re.sub(r"\boral,\s*sulcular", "oral epithelium, sulcular epithelium", question, flags=re.I)
    if compare:
        question = re.sub(r"\b(keratini[sz]ed)\s+(?:versus|vs\.?|and)\s+(non[ -]?keratini[sz]ed) epithelium", r"\1 epithelium versus \2 epithelium", question, flags=re.I)
    topics = resolve_topics(question)
    if plan.context_topic:
        topics = [_subject_identity(plan.context_topic)]
    # Joint definition requests name each entity explicitly. A conjunction
    # inside a single known anatomical name remains intact.
    definitions = re.match(r"^(?:define|what is|what are)\s+(.+?)(?:[.!?]|$)", question, re.I)
    definition_subject = _subject_phrase(question) if definitions else ""
    editorial_definition = bool(definition_subject and any(re.sub(r"[\s–—-]+", " ", noun.casefold()) == re.sub(r"[\s–—-]+", " ", definition_subject.casefold()) for noun in _editorial_nouns()))
    if definitions and not editorial_definition and re.search(r"\s+and\s+", definitions[1], re.I) and not re.search(r"\b(?:head and neck|antigen and antibody|blood and blood grouping)\b", definitions[1], re.I):
        names = [_subject_phrase("Define " + noun) for noun in re.split(r"\s+and\s+", definitions[1], flags=re.I)]
        if 2 <= len(names) <= 4 and all(names):
            topics = [_subject_identity(name) for name in names]
    joined = re.match(r"^(?:discuss|describe|explain)\s+(?:histopatholog\w*|histolog\w*)\s+features\s+of\s+(.+?)\s+and\s+(.+?)(?:[.!?]|$)", question, re.I)
    if joined and not compare:
        names = [_subject_phrase("Define " + part) for part in joined.groups()]
        if all(names):
            topics = [_subject_identity(name) for name in names]
    subject = []
    # Explicit entities stop before axes/scope; a substring alias cannot
    # silently turn an unresolved longer entity into a different known one.
    if compare:
        subjects = _comparison_subjects(question)
        if subjects:
            topics = [_subject_identity(part) for part in subjects]
            subject = [re.escape(part) for part in subjects]
    elif plan.task == "viva" and (plan.audience in {"study", "research"} or re.search(r"\bMDS\b", original, re.I)):
        candidates = _comparison_subjects("Compare " + question)
        if not candidates:
            candidate = _subject_phrase("Define " + question)
            candidates = [candidate] if candidate else []
        if candidates:
            topics = [_subject_identity(candidate) for candidate in candidates]
            subject = [re.escape(candidate) for candidate in candidates]
    elif not compare and not joined and not (definitions and len(topics) > 1) and plan.task != "viva" and not plan.is_fictional_case and not plan.context_topic and plan.audience in {"study", "research"} and not re.search(r";|\s+and\s+(?:define|explain|discuss|describe|classify|enumerate|what|why|how)\b", question, re.I):
        candidate = _subject_phrase(question)
        # "Explain inflammation in necrosis" requests a facet of the known
        # subject, rather than replacing necrosis with the facet noun.
        facet_only = any(re.fullmatch(pattern, candidate, re.I) for pattern in FACET_PATTERNS.values())
        if candidate and not (topics and facet_only):
            topics = [_subject_identity(candidate)]
            subject = [re.escape(candidate)]
    facet_text = question
    for pattern in subject:
        facet_text = re.sub(r"\b(?:" + pattern + r")\b", "__subject__", facet_text, count=1, flags=re.I)
    requested = _requested_facets(facet_text)
    if len(requested) > 1 and not re.search(r"\b(?:define|definition)\b", question, re.I):
        requested = [f for f in requested if f != "definition"]
    if not topics and requested and plan.audience == "study" and not compare and plan.task != "viva" and not plan.is_fictional_case:
        cleaned = re.sub(r"^(?:explain|describe|discuss|define|classify|enumerate|what is|what are)\s+", "", question, flags=re.I)
        matches = [m for name, pattern in FACET_PATTERNS.items() if name != "definition" for m in [re.search(pattern, cleaned, re.I)] if m]
        stop = min((m.start() for m in matches), default=len(cleaned))
        candidate = cleaned[:stop].split(".")[0].split(":")[0].strip(" ,;:?!")
        if not candidate:
            target = re.search(r"\bof\s+(.+?)(?:[.!?:]|$)", cleaned, re.I)
            candidate = target[1] if target else ""
        candidate = re.sub(r"\b(?:in|for|during|under|with)\s+.*$", "", candidate, flags=re.I).strip()
        candidate = _subject_phrase("Define " + candidate) if candidate else ""
        if candidate and candidate.casefold() not in {"a", "an", "the", "how", "and"} and not re.search(r"\b(?:its|their|that|these|my|your|i|answer|essay)\b", candidate, re.I):
            topics = [_subject_identity(candidate)]
    if not topics and requested and context_topic:
        topics = [_subject_identity(context_topic)]
    marks = re.search(r"\b(\d{1,3})[ -]marks?\b", original, re.I)
    plan.marks = int(marks[1]) if marks and 1 <= int(marks[1]) <= 100 else None
    if compare:
        plan.task = "compare"
        if not requested:
            requested = (["cellular_features", "membrane_changes", "nuclear_changes", "inflammation", "outcome"] if set(topics) == {"apoptosis", "necrosis"}
                         else ["clinical_features", "radiographic_features", "histopathology"] if {"odontogenic_keratocyst", "dentigerous_cyst"} <= set(topics)
                         else ["definition"])
        plan.comparison_axes = requested
    elif plan.is_fictional_case:
        plan.task = "fictional_case"
        plan.intent = "concept_explanation"
        plan.medical_audience = "research" if plan.audience == "research" else "student"
        requested = list(dict.fromkeys([*requested, "differential_diagnosis", "investigations"]))
        if not topics:
            finding = re.search(r"\b(?:white[ -]patch|red[ -]patch|molar pain|tooth pain|dental pain|oral swelling|jaw swelling|overjet)\b", question, re.I)
            topics = [_subject_identity(finding[0])] if finding else []
    elif plan.task not in {"viva", "quiz", "revise", "review_answer"}:
        if any(f in requested for f in ("intrinsic_pathway", "extrinsic_pathway", "stages", "epithelial_mesenchymal_interactions")) or "mechanism" in requested and len(requested) <= 2:
            plan.task = "mechanism"
        elif "architectural_features" in requested or "cytological_features" in requested:
            plan.task = "histology"
        elif re.search(r"\b(?:essay|short note|long answer)\b", original, re.I) or len(requested) >= 3:
            plan.task = "essay"
        elif re.search(r"\b(?:classify|enumerate)\b", original, re.I):
            plan.task = "classification"
        elif re.search(r"\b(?:slide discussion|slide description)\b", original, re.I):
            plan.task = "slide_discussion"
        elif re.match(r"\s*(?:define|what is|what are)\b", original, re.I) and topics:
            plan.task = "definition"
    if not requested and topics:
        requested = ["mechanism" if plan.task == "mechanism" else "definition"]
    # Preserve existing basic mechanism operations; only registry-resolved
    # requests gain this additional contract.
    scope = "; ".join(plan.qualifiers)
    trailing_scope = re.search(r"\b(?:in|for|during|under|with|following|after|before)\s+[^.!?:]+$", question.strip(" .!?"), re.I)
    if trailing_scope and not _pedagogic_scope(trailing_scope[0]) and (re.match(r"(?:following|after|before)\b", trailing_scope[0], re.I) or not resolve_topics(trailing_scope[0])):
        scope = trailing_scope[0]
        if compare:
            topics = [t.split("_for_")[0].split("_in_")[0] if t.startswith("local:") else t for t in topics]
    plan.canonical_topics = topics
    plan.primary_topic_id = topics[0] if topics else None
    plan.needs_clarification = ((unresolved or continuation) and not context_topic or plan.is_fictional_case) and not topics
    plan.facets = [RequestedFacet(topic_id=t, facet=f, query=f"{topic_name(t)} {f.replace('_', ' ')}" + (f" {scope}" if scope else ""), scope=scope)
                   for t in topics for f in requested]
    # Separate requests retain their own entity, facets and clinical scope.
    # A comparison intentionally shares axes; ordinary conjunctions do not.
    clauses = _operation_clauses(question)
    if plan.task != "viva" and not plan.is_fictional_case and len(clauses) > 1:
        scoped_facets = []
        referenced_topics = []
        comparison_axes = []
        clause_needs_clarification = False
        for clause in clauses:
            inherited_topic = topic_name(scoped_facets[-1].topic_id) if scoped_facets else context_topic
            if len(referenced_topics) > 1 and re.search(r"\b(?:both conditions|both entities|their|each measure)\b", clause, re.I):
                for identity in referenced_topics:
                    expanded = re.sub(r"\b(?:both conditions|both entities|their)\b", topic_name(identity), clause, flags=re.I)
                    scoped_facets.extend(plan_question(expanded, plan.audience).facets)
                continue
            clause_plan = plan_question(clause.strip(), plan.audience, inherited_topic)
            clause_needs_clarification |= clause_plan.needs_clarification
            scoped_facets.extend(clause_plan.facets)
            referenced_topics = clause_plan.canonical_topics
            if clause_plan.task == "compare":
                comparison_axes.extend(clause_plan.comparison_axes)
        if scoped_facets:
            seen = set()
            plan.facets = []
            for facet in scoped_facets:
                key = (facet.topic_id, facet.facet, facet.scope)
                if key not in seen:
                    seen.add(key)
                    plan.facets.append(facet)
            topics = list(dict.fromkeys(f.topic_id for f in scoped_facets))
            plan.canonical_topics = topics
            plan.primary_topic_id = topics[0]
            plan.needs_clarification = clause_needs_clarification
            if compare:
                plan.comparison_axes = list(dict.fromkeys(comparison_axes))
    if topics and plan.task == "viva":
        plan.topic = topic_name(topics[0])
    if topics and plan.task not in {"viva", "quiz", "revise", "review_answer"}:
        plan.subquestions = [f.query for f in plan.facets] or [question]
        plan.topic = topic_name(topics[0])
        if plan.medical_audience != "patient" or not personal:
            plan.medical_audience = "research" if plan.audience == "research" else "student"
    if plan.intent != "symptom_information":
        if plan.task == "compare":
            plan.intent = "comparison"
        elif plan.task == "mechanism":
            plan.intent = "mechanism"
    return plan

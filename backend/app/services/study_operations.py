"""Declared operations over admitted source-checked notes, never faculty grades."""

import re

from backend.app.errors import envelope

PILOT = (
    "epithelium-overview",
    "mds-pulp",
    "mds-periodontal-ligament",
    "mds-cementum",
    "mds-junctional-epithelium",
    "mds-salivary-glands",
    "mds-amelogenesis",
    "mds-he",
    "mds-ihc",
    "mds-fixation",
)
MECHANISMS = {
    "osmosis",
    "diffusion",
    "crossbridge",
    "muscle-contraction",
    "glycolysis",
    "competitive-inhibition",
    "mds-amelogenesis",
}


def normalize(value):
    return " ".join(value.casefold().strip(" .?!").split())


def find_unit(teacher, topic):
    return next(
        (
            u
            for u in getattr(teacher, "units", ())
            if any(normalize(topic) == normalize(t) for t in u.get("topics", []))
        ),
        None,
    )


def topic_capabilities(teacher):
    topics = []
    for unit in getattr(teacher, "units", ()):
        ids = unit["citation_ids"]
        metadata = getattr(teacher, "metadata", {})
        mappings = sorted({s for key in ids for s in metadata.get(key, {}).get("syllabus_ids", [])})
        topics.append(
            dict(
                id=unit["id"],
                topic=unit["topics"][0],
                aliases=unit["topics"],
                source_ids=ids,
                source_hashes=unit.get("source_hashes", {}),
                clinical_review="pending",
                pilot=unit["id"] in PILOT,
                curriculum_ids=mappings,
                curriculum_mapping_status="source_topic_mapping" if mappings else "not_mapped",
                operations={
                    "define": "source_checked_note",
                    "explain": "source_checked_note",
                    "compare": "basic_definition_comparison",
                    "mechanism": "bounded_note" if unit["id"] in MECHANISMS else "not_declared",
                    "fictional_case": "reflection_exercise_only",
                    "viva": "source_based_ungraded",
                    "review_answer": "reference_rubric_only",
                },
            )
        )
    return {
        "version": getattr(teacher, "version", None),
        "topics": topics,
        "coverage_scope": "Admitted prepared notes only, not full curriculum coverage or practical competence.",
        "review_status": "developer_checked_faculty_review_pending",
    }


def bound_result(teacher, units, **extra):
    ids = {key for u in units for key in u["citation_ids"]}
    sources = teacher.references.id_records
    if not ids <= sources.keys():
        return None
    return envelope(
        "ok",
        "medical_education",
        "Source-based study activity",
        claims=[dict(text=u["text"], citation_ids=u["citation_ids"]) for u in units],
        citations=[sources[k].citation() for k in sorted(ids)],
        clinical_review=False,
        teaching_version=teacher.version,
        limitations=[
            "Only these source-bound notes are covered. Faculty review and validated grading are pending."
        ],
        **extra,
    )


def operation_answer(plan, teacher):
    if not teacher or plan.intent == "symptom_information":
        return None
    q = plan.original_question.strip(" .?!")
    match = re.fullmatch(
        r"(?:compare|what is the difference between|differences between)\s+(.+?)\s+(?:and|vs\.?|versus)\s+(.+)",
        q,
        re.I,
    )
    if match:
        left, right = (find_unit(teacher, part) for part in match.groups())
        if left and right and left["id"] != right["id"]:
            return bound_result(
                teacher,
                [left, right],
                task_completion=True,
                comparison={
                    "scope": "Basic definitions and properties in these notes; no exhaustive clinical comparison.",
                    "rows": [
                        {"topic": u["topics"][0], "claim_index": i}
                        for i, u in enumerate([left, right])
                    ],
                },
            )
    review = re.fullmatch(
        r"review my answer (?:on|about|to)\s+([^:]+):\s*(.{1,2000})", q, re.I | re.S
    )
    fictional = re.fullmatch(
        r"(?:apply|practise)\s+(.+?)\s+(?:to|with|in)\s+a fictional case", q, re.I
    )
    mechanism = re.fullmatch(
        r"(?:explain (?:the )?mechanism of|how does)\s+(.+?)(?: work)?", q, re.I
    )
    if review or fictional:
        topic = review[1] if review else fictional[1]
        unit = find_unit(teacher, topic)
        if unit:
            result = bound_result(
                teacher,
                [unit],
                task_completion=False,
                answer_review={
                    "topic": topic,
                    "grading": "self_assessment_only",
                    "submitted_answer": review[2] if review else "",
                    "criteria": [
                        "Check your definition against the reference.",
                        "Explain the relevant mechanism and retain its qualifications.",
                        "Identify claims not supported by the reference; seek faculty feedback.",
                    ],
                    "fictional_prompt": f"In a fictional teaching discussion, explain {topic} using the reference, then identify what further context would be needed."
                    if fictional
                    else "",
                    "review_status": "qualified_assessment_pending",
                },
            )
            if result:
                result["status"] = "partial"
                result["message"] = (
                    "Reference and self-assessment rubric provided; individual medical grading or case interpretation is not supported."
                )
            return result
    if mechanism:
        unit = find_unit(teacher, mechanism[1])
        if unit and unit["id"] in MECHANISMS:
            return bound_result(
                teacher,
                [unit],
                task_completion=True,
                operation_scope="Mechanism within the admitted note only.",
            )
    return None

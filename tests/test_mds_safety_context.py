from backend.app.services.policy import check_policy
from backend.app.services.question_plan import plan_question


def test_current_severe_breathing_difficulty_is_urgent_without_swelling():
    assert check_policy("I have severe difficulty breathing right now.")["status"] == "urgent_guidance"
    assert check_policy("I had severe difficulty breathing last year.") is None
    assert check_policy("Fictional case: discuss severe difficulty breathing.") is None


def test_diagnose_my_lesion_cannot_hide_in_student_or_fictional_wording():
    assert check_policy("Diagnose my persistent white tongue patch definitively.")["status"] == "unsupported_input"
    assert check_policy("Fictional case: diagnose my tongue patch definitively.")["status"] == "unsupported_input"
    assert check_policy("Fictional case: discuss the differential diagnosis of a tongue patch.") is None


def test_comparison_context_applies_to_both_entities():
    plan = plan_question("Compare diffusion and osmosis for dialysis", "study")
    assert all("dialysis" in f.scope for f in plan.facets)
    scoped = plan_question("Define oral epithelium in diabetes", "study")
    assert scoped.facets[0].scope == "in diabetes"

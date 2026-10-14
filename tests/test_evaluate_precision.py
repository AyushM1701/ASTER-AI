from scripts.evaluate_teaching_precision import inspect_fit


def answer(*texts, **extra):
    return {"status": "ok", "claims": [{"text": text} for text in texts],
            "citations": [{"section": "", "title": "", "excerpt": text} for text in texts], **extra}


def test_wrong_extra_source_fails_even_if_the_first_source_matches():
    case = {"status": "ok", "source_pattern": "ST depression", "forbidden_pattern": "St. John"}
    score = inspect_fit(case, answer("ST depression is discussed here.", "St. John's wort for depression."))
    assert not score["pass"]
    assert score["relevant_citations"] == 1
    assert score["emitted_citations"] == 2


def test_silent_compound_omission_fails_partial_case():
    case = {"status": "partial", "source_pattern": "osmosis", "missing": "blorptosis"}
    assert not inspect_fit(case, answer("Osmosis is discussed here."))["pass"]
    assert inspect_fit(case, answer("Osmosis is discussed here.", unsupported_topics=["blorptosis"]))["pass"]


def test_abstention_and_each_required_topic_are_scored_separately():
    assert inspect_fit({"status": "not_handled"}, None)["pass"]
    case = {"status": "ok", "required_patterns": ["osmosis", "glomerul"]}
    assert not inspect_fit(case, answer("Osmosis is discussed here."))["pass"]
    assert inspect_fit(case, answer("Osmosis is discussed here.", "Glomerular filtration is discussed here."))["pass"]

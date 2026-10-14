"""Larger libraries must retain safety checks without repeating every scan."""

import pytest

from backend.app.services import teaching
from tests.test_mbbs_teaching import teaching_release
from tests.test_teaching_audit import store_for


def test_unchanged_passages_are_screened_once_but_changed_text_is_rescreened(tmp_path, monkeypatch):
    root, _ = teaching_release(tmp_path)
    store = store_for(root)
    assert store.answer("Explain osmosis")["status"] == "ok"
    calls = []
    original = teaching.record_scope

    def counted(*args):
        calls.append(args)
        return original(*args)

    monkeypatch.setattr(teaching, "record_scope", counted)
    assert store.answer("Explain glomerular filtration")["status"] == "ok"
    assert not calls, "Unchanged source passages were re-screened for another question"
    row = store.records[2]
    row.text = "Osmosis: take 20 mg each day."
    assert store.answer("Explain osmosis") is None
    assert calls, "Changed content must invalidate its derived safety checks"


@pytest.mark.parametrize("text", ["Take 20 mg each day.", "Take 0.5 ml each day.", "Take 5 mg."])
def test_direct_dose_instructions_are_not_teaching_passages(text):
    assert not teaching.safe_teaching_text(text)

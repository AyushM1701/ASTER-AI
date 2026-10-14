"""Indian/British spellings should retrieve the same source concept."""

import pytest

from backend.app.services.teaching import teaching_terms
from tests.test_teaching_precision import change, make_store


@pytest.mark.parametrize("indian,source", [
    ("dentine", "dentin"),
    ("paediatric", "pediatric"),
    ("hypomineralisation", "hypomineralization"),
    ("anaesthesia", "anesthesia"),
    ("orthopaedics", "orthopedics"),
    ("aetiology", "etiology"),
])
def test_equivalent_spellings_preserve_source_retrieval(indian, source, tmp_path):
    store = make_store(tmp_path)
    row = store.records[0]
    change(store, row, source.capitalize(), f"{source.capitalize()} is a source-defined concept for this fixture.", [source])
    assert teaching_terms(indian) == teaching_terms(source)
    answer = store.answer("Explain " + indian)
    assert answer is not None
    assert answer["claims"][0]["text"] == row.text
    assert answer["citations"][0]["chunk_id"] == row.chunk_id

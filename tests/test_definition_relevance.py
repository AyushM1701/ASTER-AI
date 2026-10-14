import pytest

from tests.test_knowledge_v2 import make_store, note


@pytest.mark.parametrize('backend', ['lexical', 'hybrid'])
def test_definition_prefers_subject_section_over_incidental_mention(tmp_path, backend):
    focused = note(section='Early development / Apoptosis', topics=['apoptosis'],
                   text='Apoptosis reference with its full qualifications.')
    incidental = note(section='Periodontium development / Overview', topics=['apoptosis'],
                      text='Periodontal development reference mentioning apoptosis.')
    store = make_store(tmp_path, [focused, incidental])
    if backend == 'hybrid':
        class Dense:
            def scores(self, question, ids):
                return {key: 1.0 for key in ids}
        store.dense = Dense()
        store.settings.retrieval_backend = 'hybrid'
    result = store.search('What is apoptosis?')
    assert [r.section for r in result] == [focused.section]
    assert result[0].text == focused.text
    assert len(store.search('Compare apoptosis during development')) == 2


def test_definition_keeps_candidates_when_no_heading_matches(tmp_path):
    store = make_store(tmp_path, [note(section='Definition'), note(section='Causes')])
    assert len(store.search('What is anemia?')) == 2


def test_teaching_answer_omits_incidental_chapter_for_definition(tmp_path):
    from tests.test_teaching_precision import change
    from tests.test_teaching_precision import make_store as teaching_store
    store = teaching_store(tmp_path)
    change(store, store.records[0], 'Early development / Apoptosis',
           'Apoptosis is discussed in this complete foundational section.', ['apoptosis'])
    change(store, store.records[1], 'Periodontium / Overview',
           'Periodontal development is discussed with an incidental mention of apoptosis.', ['apoptosis'])
    result = store.answer('What is apoptosis?')
    assert result is not None
    assert [r['section'] for r in result['citations']] == ['Early development / Apoptosis']
    # A contextual question must continue to retrieve its contextual material.
    contextual = store.answer('Explain apoptosis in periodontal development')
    assert contextual is not None
    assert contextual['citations'][0]['section'] == 'Periodontium / Overview'

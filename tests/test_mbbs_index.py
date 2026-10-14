import numpy as np
import pytest


def test_embedding_windows_include_late_qualification_without_truncation():
    from scripts.build_teaching_index import token_windows

    tokens = list(range(613))
    windows = token_windows(tokens, 254)
    assert [token for window in windows for token in window] == tokens
    assert [len(window) for window in windows] == [254, 254, 105]
    with pytest.raises(ValueError):
        token_windows(tokens, 0)


def test_pooled_vector_normalized_and_rejects_invalid_model_output():
    from scripts.build_teaching_index import pool_vectors

    vector = pool_vectors(np.array([[1., 0.], [0., 1.]]))
    assert vector == pytest.approx([2 ** -.5, 2 ** -.5])
    with pytest.raises(ValueError):
        pool_vectors(np.array([[float("nan"), 1.]]))
    with pytest.raises(ValueError):
        pool_vectors(np.array([[1., 0.], [-1., 0.]]))

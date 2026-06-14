from __future__ import annotations
import numpy as np
import pytest
from app.vector.index import load_indices, save_indices, get_index, INDEX_NAMES, DIMS


def test_index_names_are_three():
    assert len(INDEX_NAMES) == 3
    assert "query_patterns" in INDEX_NAMES
    assert "optimization_outcomes" in INDEX_NAMES
    assert "team_patterns" in INDEX_NAMES


def test_indices_load_fresh():
    load_indices()
    for name in INDEX_NAMES:
        idx = get_index(name)
        assert idx is not None
        assert idx.d == DIMS


def test_index_add_and_search():
    load_indices()
    idx = get_index("query_patterns")
    initial_count = idx.ntotal
    vec = np.random.rand(1, DIMS).astype("float32")
    vec /= np.linalg.norm(vec, axis=1, keepdims=True)
    idx.add(vec)
    assert idx.ntotal == initial_count + 1
    distances, ids = idx.search(vec, 1)
    assert ids[0][0] >= 0


def test_get_index_raises_for_unknown():
    from app.vector import index as vi
    vi._indices.clear()
    with pytest.raises(KeyError, match="not loaded"):
        get_index("nonexistent")


def test_save_and_reload():
    load_indices()
    idx = get_index("team_patterns")
    vec = np.random.rand(1, DIMS).astype("float32")
    vec /= np.linalg.norm(vec, axis=1, keepdims=True)
    idx.add(vec)
    count_before = idx.ntotal
    save_indices()
    from app.vector import index as vi
    vi._indices.clear()
    load_indices()
    assert get_index("team_patterns").ntotal == count_before

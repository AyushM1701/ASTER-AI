import pytest

from backend.app.services.workspaces import WorkspaceStore


def test_persistence_is_owned_and_does_not_create_until_opted_in(tmp_path):
    path = tmp_path / "education.sqlite3"
    store = WorkspaceStore(path)
    assert not path.exists()
    assert store.list("a", "study") == []
    assert not path.exists()
    store.put("a", "study", "osmosis", {"topic": "osmosis", "attempts": 1})
    assert WorkspaceStore(path).get("a", "study", "osmosis")["attempts"] == 1
    assert store.list("b", "study") == []
    assert store.get("b", "study", "osmosis") is None
    assert not store.delete("b", "study", "osmosis")
    assert store.delete("a", "study", "osmosis")
    assert store.list("a", "study") == []


def test_bounded_workspace_records(tmp_path):
    store = WorkspaceStore(tmp_path / "workspace.sqlite3", max_records=1)
    store.put("a", "study", "one", {"topic": "one"})
    with pytest.raises(ValueError):
        store.put("a", "study", "two", {"topic": "two"})
    store.put("a", "study", "one", {"topic": "updated"})
    assert store.get("a", "study", "one")["topic"] == "updated"


def test_clear_education_does_not_remove_other_owner(tmp_path):
    store = WorkspaceStore(tmp_path / "workspace.sqlite3")
    for kind in ("study", "research"):
        store.put("a", kind, "one", {"topic": "one"})
        store.put("b", kind, "one", {"topic": "one"})
    store.clear("a")
    assert store.list("a", "research") == []
    assert len(store.list("b", "research")) == 1

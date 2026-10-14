import pytest

from backend.app.config import Settings


@pytest.fixture(autouse=True)
def isolate_developer_dotenv(monkeypatch):
    """Engineering fixtures never inherit a developer's installed model profile."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)

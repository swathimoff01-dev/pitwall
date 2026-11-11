from pitwall.config import Settings


def test_conninfo_handles_special_chars(monkeypatch):
    monkeypatch.delenv("POSTGRES_DB", raising=False)
    s = Settings(_env_file=None, postgres_password="p@ss:w'rd", postgres_port=5433)
    info = s.admin_conninfo()
    assert "port=5433" in info
    assert "dbname=pitwall" in info


def test_empty_api_key_is_none(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    s = Settings(_env_file=None)
    assert s.google_api_key is None


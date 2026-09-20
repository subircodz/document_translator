import pytest

from document_translator.config import ConfigurationError, Settings


def test_settings_require_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_TRANSLATE_API_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        Settings.from_environment()


def test_settings_read_limits(monkeypatch):
    monkeypatch.setenv("GOOGLE_TRANSLATE_API_KEY", "test")
    monkeypatch.setenv("DOCUMENT_TRANSLATOR_MAX_UPLOAD_BYTES", "123")
    monkeypatch.setenv("DOCUMENT_TRANSLATOR_MAX_ARCHIVE_UNCOMPRESSED_BYTES", "789")
    monkeypatch.setenv("DOCUMENT_TRANSLATOR_JOB_TTL_SECONDS", "456")
    settings = Settings.from_environment()
    assert settings.max_upload_bytes == 123
    assert settings.max_archive_uncompressed_bytes == 789
    assert settings.job_ttl_seconds == 456

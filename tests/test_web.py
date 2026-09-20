from pathlib import Path

from fastapi.testclient import TestClient

from document_translator.models import Language, TranslationResult
from document_translator.web.app import STORE, app


class FakeProvider:
    def translate_many(self, requests):
        return [
            TranslationResult(
                request.source_language,
                request.target_language,
                request.text,
                f"translated-{request.text}",
            )
            for request in requests
        ]

    def supports(self, source, target):
        return source is Language.ENGLISH and target in {Language.HINDI, Language.TAMIL}


def test_home_page_lists_targets() -> None:
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert 'value="hi"' in response.text
    assert 'value="ta"' in response.text


def test_status_missing_job() -> None:
    response = TestClient(app).get("/api/translations/missing")
    assert response.status_code == 404


def test_upload_rejects_non_docx(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_TRANSLATE_API_KEY", "test")
    response = TestClient(app).post(
        "/translate",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        data={"targets": "hi"},
    )
    assert response.status_code == 400
    assert "docx" in response.json()["detail"]


def test_upload_rejects_missing_api_key(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_TRANSLATE_API_KEY", raising=False)
    response = TestClient(app).post(
        "/translate",
        files={"file": ("notes.docx", b"not-a-real-docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"targets": "hi"},
    )
    assert response.status_code == 503

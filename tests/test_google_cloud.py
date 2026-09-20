import json
from urllib.error import HTTPError

import pytest

from document_translator.models import Language, TranslationRequest
from document_translator.translation.errors import TranslationProviderError
from document_translator.translation.google_cloud import GoogleCloudTranslationProvider


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def request_data(text: str = "Hello") -> TranslationRequest:
    return TranslationRequest(Language.ENGLISH, Language.HINDI, text)


def test_google_provider_translates_successfully() -> None:
    calls: list[object] = []

    def opener(http_request: object, timeout: float) -> FakeResponse:
        calls.append(http_request)
        return FakeResponse({"data": {"translations": [{"translatedText": "नमस्ते"}]}})

    provider = GoogleCloudTranslationProvider(api_key="secret", opener=opener)
    result = provider.translate(request_data())

    assert result.translated_text == "नमस्ते"
    assert result.source_text == "Hello"
    assert calls


def test_google_provider_batches_requests() -> None:
    calls = 0

    def opener(http_request: object, timeout: float) -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse({
            "data": {"translations": [{"translatedText": "एक"}, {"translatedText": "दो"}]}
        })

    provider = GoogleCloudTranslationProvider(api_key="secret", opener=opener, max_batch_size=2)
    results = provider.translate_many([request_data("one"), request_data("two")])

    assert calls == 1
    assert [item.translated_text for item in results] == ["एक", "दो"]


def test_google_provider_rejects_unsupported_pair() -> None:
    provider = GoogleCloudTranslationProvider(api_key="secret")
    request_value = TranslationRequest(Language.HINDI, Language.TAMIL, "नमस्ते")

    with pytest.raises(TranslationProviderError, match="Unsupported language pair"):
        provider.translate(request_value)


def test_google_provider_retries_transient_http_error() -> None:
    attempts = 0

    def opener(http_request: object, timeout: float) -> FakeResponse:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise HTTPError("https://example.test", 503, "busy", {}, None)
        return FakeResponse({"data": {"translations": [{"translatedText": "नमस्ते"}]}})

    provider = GoogleCloudTranslationProvider(api_key="secret", opener=opener, retry_delay=0)
    result = provider.translate(request_data())

    assert result.translated_text == "नमस्ते"
    assert attempts == 2


def test_google_provider_fails_after_retry_limit() -> None:
    def opener(http_request: object, timeout: float) -> FakeResponse:
        raise HTTPError("https://example.test", 503, "busy", {}, None)

    provider = GoogleCloudTranslationProvider(api_key="secret", opener=opener, max_retries=2, retry_delay=0)

    with pytest.raises(TranslationProviderError, match="HTTP 503"):
        provider.translate(request_data())

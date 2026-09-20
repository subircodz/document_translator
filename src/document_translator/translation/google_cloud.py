"""Google Cloud Translation Basic API adapter."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Callable
from urllib import error, request

from document_translator.models import Language, TranslationRequest, TranslationResult
from document_translator.translation.errors import TranslationProviderError

_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"
_INDIAN_TARGETS = frozenset({
    Language.HINDI, Language.BENGALI, Language.KANNADA,
    Language.TELUGU, Language.TAMIL, Language.MALAYALAM,
})


@dataclass(frozen=True)
class GoogleCloudTranslationProvider:
    """Translate text through Google Cloud Translation Basic API."""

    api_key: str | None = None
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    endpoint: str = _ENDPOINT
    opener: Callable[..., object] = request.urlopen

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")

    def supports(self, source: Language, target: Language) -> bool:
        return source is Language.ENGLISH and target in _INDIAN_TARGETS

    def translate(self, request_data: TranslationRequest) -> TranslationResult:
        if not self.supports(request_data.source_language, request_data.target_language):
            raise TranslationProviderError(
                "Unsupported language pair",
                source_language=request_data.source_language,
                target_language=request_data.target_language,
            )

        api_key = self.api_key or os.getenv("GOOGLE_TRANSLATE_API_KEY")
        if not api_key:
            raise TranslationProviderError(
                "GOOGLE_TRANSLATE_API_KEY is not configured",
                source_language=request_data.source_language,
                target_language=request_data.target_language,
            )

        payload = {
            "q": request_data.text,
            "source": request_data.source_language.value,
            "target": request_data.target_language.value,
            "format": "text",
        }
        response = self._post(payload, request_data, api_key)
        try:
            translated = response["data"]["translations"][0]["translatedText"]
        except (KeyError, IndexError, TypeError) as exc:
            raise TranslationProviderError(
                "Google Cloud returned an invalid translation response",
                source_language=request_data.source_language,
                target_language=request_data.target_language,
            ) from exc
        if not isinstance(translated, str):
            raise TranslationProviderError(
                "Google Cloud returned non-text translation content",
                source_language=request_data.source_language,
                target_language=request_data.target_language,
            )
        return TranslationResult(
            source_language=request_data.source_language,
            target_language=request_data.target_language,
            source_text=request_data.text,
            translated_text=translated,
        )

    def _post(self, payload: dict[str, object], request_data: TranslationRequest, api_key: str) -> dict[str, object]:
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            self.endpoint,
            data=body,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "x-goog-api-key": api_key,
            },
            method="POST",
        )
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                with self.opener(http_request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except error.HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == attempts - 1:
                    raise TranslationProviderError(
                        f"Google Cloud translation request failed (HTTP {exc.code})",
                        source_language=request_data.source_language,
                        target_language=request_data.target_language,
                    ) from exc
            except (error.URLError, TimeoutError, OSError) as exc:
                if attempt == attempts - 1:
                    raise TranslationProviderError(
                        "Google Cloud translation request failed",
                        source_language=request_data.source_language,
                        target_language=request_data.target_language,
                    ) from exc
            time.sleep(self.retry_delay * (2 ** attempt))
        raise AssertionError("unreachable")

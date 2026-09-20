"""Google Cloud Translation Basic API adapter."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
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
    max_batch_size: int = 128
    endpoint: str = _ENDPOINT
    opener: Callable[..., object] = request.urlopen

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")
        if not 1 <= self.max_batch_size <= 128:
            raise ValueError("max_batch_size must be between 1 and 128")

    def supports(self, source: Language, target: Language) -> bool:
        return source is Language.ENGLISH and target in _INDIAN_TARGETS

    def translate(self, request_data: TranslationRequest) -> TranslationResult:
        results = self.translate_many([request_data])
        return results[0]

    def translate_many(
        self, requests: Sequence[TranslationRequest]
    ) -> list[TranslationResult]:
        """Translate requests in bounded batches of at most 128 strings."""
        if not requests:
            return []
        first = requests[0]
        if any(
            not self.supports(item.source_language, item.target_language)
            for item in requests
        ):
            raise TranslationProviderError(
                "Unsupported language pair",
                source_language=first.source_language,
                target_language=first.target_language,
            )
        if any(
            (item.source_language, item.target_language)
            != (first.source_language, first.target_language)
            for item in requests
        ):
            raise TranslationProviderError(
                "A batch must contain one language pair",
                source_language=first.source_language,
                target_language=first.target_language,
            )

        api_key = self.api_key or os.getenv("GOOGLE_TRANSLATE_API_KEY")
        if not api_key:
            raise TranslationProviderError(
                "GOOGLE_TRANSLATE_API_KEY is not configured",
                source_language=first.source_language,
                target_language=first.target_language,
            )

        results: list[TranslationResult] = []
        for start in range(0, len(requests), self.max_batch_size):
            batch = requests[start : start + self.max_batch_size]
            payload = {
                "q": [item.text for item in batch],
                "source": first.source_language.value,
                "target": first.target_language.value,
                "format": "text",
            }
            response = self._post(payload, first, api_key)
            try:
                translations = response["data"]["translations"]
                translated_texts = [item["translatedText"] for item in translations]
            except (KeyError, IndexError, TypeError) as exc:
                raise TranslationProviderError(
                    "Google Cloud returned an invalid translation response",
                    source_language=first.source_language,
                    target_language=first.target_language,
                ) from exc
            if len(translated_texts) != len(batch) or not all(
                isinstance(text, str) for text in translated_texts
            ):
                raise TranslationProviderError(
                    "Google Cloud returned an incomplete translation batch",
                    source_language=first.source_language,
                    target_language=first.target_language,
                )
            results.extend(
                TranslationResult(
                    source_language=item.source_language,
                    target_language=item.target_language,
                    source_text=item.text,
                    translated_text=translated,
                )
                for item, translated in zip(batch, translated_texts)
            )
        return results

    def _post(
        self,
        payload: dict[str, object],
        request_data: TranslationRequest,
        api_key: str,
    ) -> dict[str, object]:
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

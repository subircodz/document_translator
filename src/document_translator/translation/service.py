"""Translation orchestration with token protection."""

from dataclasses import dataclass

from document_translator.models import TranslationRequest, TranslationResult
from document_translator.protection.tokens import protect, restore
from document_translator.translation.provider import TranslationProvider


@dataclass(frozen=True)
class TranslationService:
    """Apply token protection around a translation provider."""

    provider: TranslationProvider

    def translate(self, request: TranslationRequest) -> TranslationResult:
        return self.translate_many([request])[0]

    def translate_many(
        self, requests: list[TranslationRequest]
    ) -> list[TranslationResult]:
        """Translate requests while protecting non-translatable tokens."""
        if not requests:
            return []

        protected_requests: list[TranslationRequest] = []
        protections = []
        for request in requests:
            protected = protect(request.text)
            protections.append(protected)
            protected_requests.append(
                TranslationRequest(
                    source_language=request.source_language,
                    target_language=request.target_language,
                    text=protected.text,
                )
            )

        translate_many = getattr(self.provider, "translate_many", None)
        if callable(translate_many):
            results = translate_many(protected_requests)
        else:
            results = [self.provider.translate(request) for request in protected_requests]

        if len(results) != len(requests):
            raise RuntimeError("Translation provider returned an incomplete batch.")

        return [
            TranslationResult(
                source_language=request.source_language,
                target_language=request.target_language,
                source_text=request.text,
                translated_text=restore(result.translated_text, protected.tokens),
            )
            for request, result, protected in zip(
                requests, results, protections, strict=True
            )
        ]

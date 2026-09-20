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
        protected = protect(request.text)
        protected_request = TranslationRequest(
            source_language=request.source_language,
            target_language=request.target_language,
            text=protected.text,
        )
        result = self.provider.translate(protected_request)
        return TranslationResult(
            source_language=result.source_language,
            target_language=result.target_language,
            source_text=request.text,
            translated_text=restore(result.translated_text, protected.tokens),
        )

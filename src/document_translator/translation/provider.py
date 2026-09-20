"""Provider abstraction for translation engines."""

from typing import Protocol

from document_translator.models import Language, TranslationRequest, TranslationResult


class TranslationProvider(Protocol):
    """Contract implemented by external translation providers."""

    def translate(self, request: TranslationRequest) -> TranslationResult:
        """Translate one request."""
        ...

    def supports(self, source: Language, target: Language) -> bool:
        """Return whether this provider supports the language pair."""
        ...

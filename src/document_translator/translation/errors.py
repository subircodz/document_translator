"""Translation-provider error types."""

from document_translator.models import Language


class TranslationProviderError(RuntimeError):
    """Raised when a translation provider cannot complete a request."""

    def __init__(self, message: str, *, source_language: Language, target_language: Language) -> None:
        super().__init__(message)
        self.source_language = source_language
        self.target_language = target_language

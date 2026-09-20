from dataclasses import dataclass

from document_translator.models import Language, TranslationRequest, TranslationResult
from document_translator.translation.service import TranslationService


@dataclass
class FakeProvider:
    received_text: str | None = None

    def supports(self, source: Language, target: Language) -> bool:
        return True

    def translate(self, request: TranslationRequest) -> TranslationResult:
        self.received_text = request.text
        return TranslationResult(
            source_language=request.source_language,
            target_language=request.target_language,
            source_text=request.text,
            translated_text=f"अनुवाद: {request.text}",
        )


def test_translation_service_protects_and_restores_tokens() -> None:
    provider = FakeProvider()
    service = TranslationService(provider)
    source = "Contact test@example.com for ORD-10291 at https://example.com."

    result = service.translate(TranslationRequest(Language.ENGLISH, Language.HINDI, source))

    assert "test@example.com" not in (provider.received_text or "")
    assert "ORD-10291" not in (provider.received_text or "")
    assert "https://example.com." not in (provider.received_text or "")
    assert result.source_text == source
    assert "test@example.com" in result.translated_text
    assert "ORD-10291" in result.translated_text
    assert "https://example.com." in result.translated_text

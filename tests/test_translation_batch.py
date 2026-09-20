from dataclasses import dataclass

from document_translator.models import Language, TranslationRequest, TranslationResult
from document_translator.translation.service import TranslationService


@dataclass
class BatchProvider:
    requests: list[TranslationRequest] | None = None

    def supports(self, source: Language, target: Language) -> bool:
        return True

    def translate(self, request: TranslationRequest) -> TranslationResult:
        raise AssertionError("single-request path should not be used")

    def translate_many(
        self, requests: list[TranslationRequest]
    ) -> list[TranslationResult]:
        self.requests = requests
        return [
            TranslationResult(
                item.source_language,
                item.target_language,
                item.text,
                f"अनुवाद: {item.text}",
            )
            for item in requests
        ]


def test_translation_service_uses_provider_batch_and_restores_tokens() -> None:
    provider = BatchProvider()
    service = TranslationService(provider)
    requests = [
        TranslationRequest(
            Language.ENGLISH,
            Language.HINDI,
            "Contact test@example.com",
        ),
        TranslationRequest(
            Language.ENGLISH,
            Language.HINDI,
            "Order ORD-12345",
        ),
    ]

    results = service.translate_many(requests)

    assert len(provider.requests or []) == 2
    assert "test@example.com" not in provider.requests[0].text
    assert "ORD-12345" not in provider.requests[1].text
    assert "test@example.com" in results[0].translated_text
    assert "ORD-12345" in results[1].translated_text

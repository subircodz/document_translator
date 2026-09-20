from dataclasses import dataclass

from document_translator.document.model import DocumentModel, ParagraphModel, RunModel, TableModel
from document_translator.models import Language, TranslationRequest, TranslationResult
from document_translator.translation.service import TranslationService
from document_translator.translation.document import translate_document


@dataclass
class FakeProvider:
    def supports(self, source: Language, target: Language) -> bool:
        return True

    def translate(self, request: TranslationRequest) -> TranslationResult:
        return TranslationResult(
            source_language=request.source_language,
            target_language=request.target_language,
            source_text=request.text,
            translated_text=f"अनुवाद: {request.text}",
        )


def test_translate_document_preserves_supported_structure() -> None:
    document = DocumentModel(
        blocks=(
            ParagraphModel(
                text="Hello",
                style="Heading 1",
                runs=(RunModel("Hello", bold=True),),
            ),
            TableModel(
                rows=(
                    ((ParagraphModel("Name", "Normal", (RunModel("Name"),)),),),
                )
            ),
        )
    )
    translated = translate_document(
        document, TranslationService(FakeProvider()), Language.HINDI
    )
    assert translated.blocks[0].text == "अनुवाद: Hello"
    assert translated.blocks[0].style == "Heading 1"
    assert translated.blocks[0].runs[0].bold is True
    table = translated.blocks[1]
    assert table.rows[0][0][0].text == "अनुवाद: Name"

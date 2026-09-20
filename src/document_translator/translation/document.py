"""Document-level translation orchestration."""

from dataclasses import replace

from document_translator.document.model import DocumentModel, ParagraphModel, TableModel
from document_translator.models import Language, TranslationRequest
from document_translator.translation.service import TranslationService


def _translate_paragraph(
    paragraph: ParagraphModel, service: TranslationService, target: Language
) -> ParagraphModel:
    if not paragraph.text.strip():
        return paragraph
    result = service.translate(
        TranslationRequest(Language.ENGLISH, target, paragraph.text)
    )
    if paragraph.runs:
        first = paragraph.runs[0]
        runs = (replace(first, text=result.translated_text), *paragraph.runs[1:])
    else:
        runs = ()
    return replace(paragraph, text=result.translated_text, runs=runs)


def _translate_table(
    table: TableModel, service: TranslationService, target: Language
) -> TableModel:
    return TableModel(
        rows=tuple(
            tuple(
                tuple(
                    _translate_paragraph(paragraph, service, target)
                    for paragraph in cell
                )
                for cell in row
            )
            for row in table.rows
        )
    )


def translate_document(
    document: DocumentModel, service: TranslationService, target: Language
) -> DocumentModel:
    """Translate all supported text blocks while preserving document structure."""
    return DocumentModel(
        blocks=tuple(
            _translate_paragraph(block, service, target)
            if isinstance(block, ParagraphModel)
            else _translate_table(block, service, target)
            for block in document.blocks
        )
    )

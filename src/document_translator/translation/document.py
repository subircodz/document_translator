"""Document-level translation orchestration."""

from dataclasses import replace

from document_translator.document.model import DocumentModel, ParagraphModel, TableModel
from document_translator.models import Language, TranslationRequest
from document_translator.translation.service import TranslationService


def _paragraphs(document: DocumentModel) -> list[ParagraphModel]:
    paragraphs = []
    for block in document.blocks:
        if isinstance(block, ParagraphModel):
            paragraphs.append(block)
        else:
            for row in block.rows:
                for cell in row:
                    paragraphs.extend(cell)
    return paragraphs


def _translated_paragraphs(
    document: DocumentModel, service: TranslationService, target: Language
) -> dict[int, ParagraphModel]:
    paragraphs = _paragraphs(document)
    requests = [
        TranslationRequest(Language.ENGLISH, target, paragraph.text)
        for paragraph in paragraphs
        if paragraph.text.strip()
    ]
    results = iter(service.translate_many(requests))
    translated: dict[int, ParagraphModel] = {}
    for paragraph in paragraphs:
        if not paragraph.text.strip():
            translated[id(paragraph)] = paragraph
            continue
        result = next(results)
        if paragraph.runs:
            first = paragraph.runs[0]
            runs = (replace(first, text=result.translated_text), *paragraph.runs[1:])
        else:
            runs = ()
        translated[id(paragraph)] = replace(
            paragraph, text=result.translated_text, runs=runs
        )
    return translated


def translate_document(
    document: DocumentModel, service: TranslationService, target: Language
) -> DocumentModel:
    """Translate all supported text blocks using one provider batch."""
    translated = _translated_paragraphs(document, service, target)

    def translate_paragraph(paragraph: ParagraphModel) -> ParagraphModel:
        return translated[id(paragraph)]

    def translate_table(table: TableModel) -> TableModel:
        return TableModel(
            rows=tuple(
                tuple(
                    tuple(translate_paragraph(paragraph) for paragraph in cell)
                    for cell in row
                )
                for row in table.rows
            )
        )

    return DocumentModel(
        blocks=tuple(
            translate_paragraph(block)
            if isinstance(block, ParagraphModel)
            else translate_table(block)
            for block in document.blocks
        )
    )

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
    requests: list[TranslationRequest] = []
    request_keys: list[tuple[int, int | None]] = []

    for paragraph in paragraphs:
        if paragraph.runs:
            for index, run in enumerate(paragraph.runs):
                if run.text.strip():
                    requests.append(
                        TranslationRequest(Language.ENGLISH, target, run.text)
                    )
                    request_keys.append((id(paragraph), index))
        elif paragraph.text.strip():
            requests.append(
                TranslationRequest(Language.ENGLISH, target, paragraph.text)
            )
            request_keys.append((id(paragraph), None))

    results = service.translate_many(requests)
    if len(results) != len(request_keys):
        raise RuntimeError("Translation service returned an incomplete batch.")

    translated_texts = dict(
        zip(request_keys, (result.translated_text for result in results), strict=True)
    )

    translated: dict[int, ParagraphModel] = {}
    for paragraph in paragraphs:
        if paragraph.runs:
            runs = tuple(
                replace(
                    run,
                    text=translated_texts.get((id(paragraph), index), run.text),
                )
                for index, run in enumerate(paragraph.runs)
            )
            translated_text = "".join(run.text for run in runs)
            translated[id(paragraph)] = replace(
                paragraph, text=translated_text, runs=runs
            )
        elif paragraph.text.strip():
            translated[id(paragraph)] = replace(
                paragraph,
                text=translated_texts[(id(paragraph), None)],
            )
        else:
            translated[id(paragraph)] = paragraph

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

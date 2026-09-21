"""Validation rules for translated text and DOCX structure."""

from document_translator.document.model import (
    DocumentBlock,
    DocumentModel,
    ParagraphModel,
    TableModel,
)
from document_translator.models import Language, TranslationResult
from document_translator.protection.tokens import protect
from document_translator.validation.report import (
    DocumentValidationItem,
    DocumentValidationReport,
    TranslationValidationReport,
    ValidationIssue,
    ValidationStatus,
)

_REPLACEMENT_CHARACTER = "\ufffd"


def validate_translation(result: TranslationResult) -> TranslationValidationReport:
    """Validate translated content, protected tokens, and Unicode integrity."""
    issues: list[ValidationIssue] = []

    if not result.source_text.strip():
        return TranslationValidationReport(
            source_language=result.source_language,
            target_language=result.target_language,
            source_text=result.source_text,
            translated_text=result.translated_text,
            status=ValidationStatus.PASS,
            issues=(),
        )

    if not result.translated_text.strip():
        issues.append(
            ValidationIssue(
                "missing_translation",
                "Translated content is empty or whitespace-only.",
                ValidationStatus.FAILURE,
            )
        )

    if result.source_text.strip() and result.translated_text == result.source_text:
        issues.append(
            ValidationIssue(
                "unchanged_translation",
                "Translated content is identical to the source content.",
                ValidationStatus.WARNING,
            )
        )

    try:
        result.translated_text.encode("utf-8", "strict")
    except UnicodeEncodeError:
        issues.append(
            ValidationIssue(
                "invalid_unicode",
                "Translated content contains invalid Unicode characters.",
                ValidationStatus.FAILURE,
            )
        )

    if _REPLACEMENT_CHARACTER in result.translated_text:
        issues.append(
            ValidationIssue(
                "unicode_replacement_character",
                "Translated content contains the Unicode replacement character.",
                ValidationStatus.FAILURE,
            )
        )

    protected = protect(result.source_text)
    for placeholder, original in protected.tokens.items():
        if original not in result.translated_text:
            issues.append(
                ValidationIssue(
                    "missing_protected_token",
                    f"Protected token was not restored: {original}",
                    ValidationStatus.FAILURE,
                )
            )
        if placeholder in result.translated_text:
            issues.append(
                ValidationIssue(
                    "unrestored_placeholder",
                    f"Protected placeholder remains in output: {placeholder}",
                    ValidationStatus.FAILURE,
                )
            )

    status = ValidationStatus.PASS
    if any(issue.severity is ValidationStatus.FAILURE for issue in issues):
        status = ValidationStatus.FAILURE
    elif issues:
        status = ValidationStatus.WARNING

    return TranslationValidationReport(
        source_language=result.source_language,
        target_language=result.target_language,
        source_text=result.source_text,
        translated_text=result.translated_text,
        status=status,
        issues=tuple(issues),
    )


def _paragraph_text(paragraph: ParagraphModel) -> str:
    """Return paragraph text, falling back to its run content."""
    return paragraph.text or "".join(run.text for run in paragraph.runs)


def _translation_result(
    source: ParagraphModel,
    translated: ParagraphModel,
    source_language: Language,
    target_language: Language,
) -> TranslationResult:
    return TranslationResult(
        source_language=source_language,
        target_language=target_language,
        source_text=_paragraph_text(source),
        translated_text=_paragraph_text(translated),
    )


def _validate_paragraph(
    source: ParagraphModel,
    translated: ParagraphModel,
    location: str,
    source_language: Language,
    target_language: Language,
) -> DocumentValidationItem:
    return DocumentValidationItem(
        location=location,
        report=validate_translation(
            _translation_result(
                source,
                translated,
                source_language,
                target_language,
            )
        ),
    )


def _structural_issue(code: str, message: str) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        severity=ValidationStatus.FAILURE,
    )


def _validate_table(
    source: TableModel,
    translated: TableModel,
    location: str,
    source_language: Language,
    target_language: Language,
) -> tuple[list[DocumentValidationItem], list[ValidationIssue]]:
    items: list[DocumentValidationItem] = []
    issues: list[ValidationIssue] = []

    if len(source.rows) != len(translated.rows):
        issues.append(
            _structural_issue(
                "table_row_count_mismatch",
                f"{location}: source has {len(source.rows)} rows, "
                f"translated document has {len(translated.rows)}.",
            )
        )

    for row_index, source_row in enumerate(source.rows):
        if row_index >= len(translated.rows):
            break
        translated_row = translated.rows[row_index]
        if len(source_row) != len(translated_row):
            issues.append(
                _structural_issue(
                    "table_cell_count_mismatch",
                    f"{location}.row[{row_index}]: source has {len(source_row)} "
                    f"cells, translated document has {len(translated_row)}.",
                )
            )

        for cell_index, source_cell in enumerate(source_row):
            if cell_index >= len(translated_row):
                break
            translated_cell = translated_row[cell_index]
            if len(source_cell) != len(translated_cell):
                issues.append(
                    _structural_issue(
                        "table_paragraph_count_mismatch",
                        f"{location}.row[{row_index}].cell[{cell_index}]: "
                        f"source has {len(source_cell)} paragraphs, "
                        f"translated document has {len(translated_cell)}.",
                    )
                )

            for paragraph_index, source_paragraph in enumerate(source_cell):
                if paragraph_index >= len(translated_cell):
                    break
                items.append(
                    _validate_paragraph(
                        source_paragraph,
                        translated_cell[paragraph_index],
                        f"{location}.row[{row_index}].cell[{cell_index}]"
                        f".paragraph[{paragraph_index}]",
                        source_language,
                        target_language,
                    )
                )

    return items, issues


def _validate_block_pair(
    source: DocumentBlock,
    translated: DocumentBlock,
    location: str,
    source_language: Language,
    target_language: Language,
) -> tuple[list[DocumentValidationItem], list[ValidationIssue]]:
    if type(source) is not type(translated):
        return [], [
            _structural_issue(
                "block_type_mismatch",
                f"{location}: source block type is {type(source).__name__}, "
                f"translated block type is {type(translated).__name__}.",
            )
        ]

    if isinstance(source, ParagraphModel):
        return [
            _validate_paragraph(
                source,
                translated,
                location,
                source_language,
                target_language,
            )
        ], []

    return _validate_table(
        source,
        translated,
        location,
        source_language,
        target_language,
    )


def validate_document(
    source: DocumentModel,
    translated: DocumentModel,
    source_language: Language = Language.ENGLISH,
    target_language: Language = Language.HINDI,
) -> DocumentValidationReport:
    """Validate translated document content and supported DOCX structure."""
    items: list[DocumentValidationItem] = []
    structural_issues: list[ValidationIssue] = []

    if len(source.blocks) != len(translated.blocks):
        structural_issues.append(
            _structural_issue(
                "block_count_mismatch",
                f"Source has {len(source.blocks)} blocks, translated document "
                f"has {len(translated.blocks)}.",
            )
        )

    for block_index, source_block in enumerate(source.blocks):
        if block_index >= len(translated.blocks):
            break
        block_items, block_issues = _validate_block_pair(
            source_block,
            translated.blocks[block_index],
            f"block[{block_index}]",
            source_language,
            target_language,
        )
        items.extend(block_items)
        structural_issues.extend(block_issues)

    status = ValidationStatus.PASS
    if structural_issues or any(
        item.report.status is ValidationStatus.FAILURE for item in items
    ):
        status = ValidationStatus.FAILURE
    elif any(item.report.status is ValidationStatus.WARNING for item in items):
        status = ValidationStatus.WARNING

    return DocumentValidationReport(
        source_language=source_language,
        target_language=target_language,
        status=status,
        items=tuple(items),
        structural_issues=tuple(structural_issues),
    )

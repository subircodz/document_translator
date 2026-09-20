from document_translator.document.model import (
    DocumentModel,
    ParagraphModel,
    RunModel,
    TableModel,
)
from document_translator.models import Language, TranslationResult
from document_translator.validation.renderer import render_document_report
from document_translator.validation.report import ValidationStatus
from document_translator.validation.validator import (
    validate_document,
    validate_translation,
)


def result(source: str, translated: str) -> TranslationResult:
    return TranslationResult(
        source_language=Language.ENGLISH,
        target_language=Language.HINDI,
        source_text=source,
        translated_text=translated,
    )


def paragraph(text: str, style: str = "Normal") -> ParagraphModel:
    return ParagraphModel(text=text, style=style, runs=(RunModel(text=text),))


def test_validation_passes_for_valid_translation_and_restored_tokens() -> None:
    report = validate_translation(
        result(
            "Contact test@example.com for ORD-10291 at https://example.com.",
            "संपर्क test@example.com करें ORD-10291 पर https://example.com.",
        )
    )
    assert report.status is ValidationStatus.PASS
    assert report.issues == ()


def test_validation_detects_missing_translation() -> None:
    report = validate_translation(result("Hello", ""))
    assert report.status is ValidationStatus.FAILURE
    assert any(issue.code == "missing_translation" for issue in report.issues)


def test_validation_warns_when_translation_is_unchanged() -> None:
    report = validate_translation(result("Hello", "Hello"))
    assert report.status is ValidationStatus.WARNING
    assert any(issue.code == "unchanged_translation" for issue in report.issues)


def test_validation_detects_missing_protected_token() -> None:
    report = validate_translation(result("Use ORD-10291", "उपयोग करें"))
    assert report.status is ValidationStatus.FAILURE
    assert any(issue.code == "missing_protected_token" for issue in report.issues)


def test_validation_detects_unrestored_placeholder() -> None:
    report = validate_translation(
        result("Use ORD-10291", "उपयोग करें __DT_TOKEN_0000__")
    )
    assert report.status is ValidationStatus.FAILURE
    assert any(issue.code == "unrestored_placeholder" for issue in report.issues)


def test_validation_detects_unicode_replacement_character() -> None:
    report = validate_translation(result("Hello", "नमस्ते�"))
    assert report.status is ValidationStatus.FAILURE
    assert any(
        issue.code == "unicode_replacement_character" for issue in report.issues
    )


def test_document_validation_covers_paragraphs_and_tables() -> None:
    source = DocumentModel(
        blocks=(
            paragraph("Contact test@example.com"),
            TableModel(
                rows=(
                    (
                        (paragraph("Order ORD-100"),),
                        (paragraph("Amount 100"),),
                    ),
                )
            ),
        )
    )
    translated = DocumentModel(
        blocks=(
            paragraph("संपर्क test@example.com"),
            TableModel(
                rows=(
                    (
                        (paragraph("आदेश ORD-100"),),
                        (paragraph("राशि 100"),),
                    ),
                )
            ),
        )
    )
    report = validate_document(source, translated)
    assert report.status is ValidationStatus.PASS
    assert len(report.items) == 3
    assert report.structural_issues == ()


def test_document_validation_detects_structure_mismatch() -> None:
    report = validate_document(
        DocumentModel(blocks=(paragraph("Hello"),)),
        DocumentModel(blocks=(TableModel(rows=()),)),
    )
    assert report.status is ValidationStatus.FAILURE
    assert any(issue.code == "block_type_mismatch" for issue in report.structural_issues)


def test_document_validation_detects_table_shape_mismatch() -> None:
    source = DocumentModel(
        blocks=(TableModel(rows=(((paragraph("A"), paragraph("B")),),)),)
    )
    translated = DocumentModel(
        blocks=(TableModel(rows=(((paragraph("A"),),),)),)
    )
    report = validate_document(source, translated)
    assert report.status is ValidationStatus.FAILURE
    assert any(
        issue.code == "table_paragraph_count_mismatch"
        for issue in report.structural_issues
    )


def test_render_document_report_is_human_readable() -> None:
    report = validate_document(
        DocumentModel(blocks=(paragraph("Hello"),)),
        DocumentModel(blocks=(paragraph("Hello"),)),
    )
    rendered = render_document_report(report)
    assert "Document Translation Validation Report" in rendered
    assert "WARNING" in rendered
    assert "block[0]" in rendered
    assert "unchanged_translation" in rendered

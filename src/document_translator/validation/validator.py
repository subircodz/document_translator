"""Validation rules for translated text."""

from document_translator.models import TranslationResult
from document_translator.protection.tokens import protect
from document_translator.validation.report import (
    TranslationValidationReport,
    ValidationIssue,
    ValidationStatus,
)

_REPLACEMENT_CHARACTER = "\ufffd"


def validate_translation(result: TranslationResult) -> TranslationValidationReport:
    """Validate translated content, protected tokens, and Unicode integrity."""
    issues: list[ValidationIssue] = []

    if not result.translated_text.strip():
        issues.append(
            ValidationIssue(
                code="missing_translation",
                message="Translated content is empty or whitespace-only.",
                severity=ValidationStatus.FAILURE,
            )
        )

    if result.source_text.strip() and result.translated_text == result.source_text:
        issues.append(
            ValidationIssue(
                code="unchanged_translation",
                message="Translated content is identical to the source content.",
                severity=ValidationStatus.WARNING,
            )
        )

    try:
        result.translated_text.encode("utf-8", "strict")
    except UnicodeEncodeError:
        issues.append(
            ValidationIssue(
                code="invalid_unicode",
                message="Translated content contains invalid Unicode characters.",
                severity=ValidationStatus.FAILURE,
            )
        )

    if _REPLACEMENT_CHARACTER in result.translated_text:
        issues.append(
            ValidationIssue(
                code="unicode_replacement_character",
                message="Translated content contains the Unicode replacement character.",
                severity=ValidationStatus.FAILURE,
            )
        )

    protected = protect(result.source_text)
    for placeholder, original in protected.tokens.items():
        if original not in result.translated_text:
            issues.append(
                ValidationIssue(
                    code="missing_protected_token",
                    message=f"Protected token was not restored: {original}",
                    severity=ValidationStatus.FAILURE,
                )
            )
        if placeholder in result.translated_text:
            issues.append(
                ValidationIssue(
                    code="unrestored_placeholder",
                    message=f"Protected placeholder remains in output: {placeholder}",
                    severity=ValidationStatus.FAILURE,
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

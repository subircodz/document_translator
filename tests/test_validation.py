from document_translator.models import Language, TranslationResult
from document_translator.validation.report import ValidationStatus
from document_translator.validation.validator import validate_translation


def result(source: str, translated: str) -> TranslationResult:
    return TranslationResult(
        source_language=Language.ENGLISH,
        target_language=Language.HINDI,
        source_text=source,
        translated_text=translated,
    )


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
    report = validate_translation(result("Hello", "नमस्ते\ufffd"))

    assert report.status is ValidationStatus.FAILURE
    assert any(
        issue.code == "unicode_replacement_character" for issue in report.issues
    )

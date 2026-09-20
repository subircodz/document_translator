"""Validation report domain models."""

from dataclasses import dataclass
from enum import StrEnum

from document_translator.models import Language


class ValidationStatus(StrEnum):
    PASS = "pass"
    WARNING = "warning"
    FAILURE = "failure"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: ValidationStatus


@dataclass(frozen=True)
class TranslationValidationReport:
    source_language: Language
    target_language: Language
    source_text: str
    translated_text: str
    status: ValidationStatus
    issues: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return self.status is not ValidationStatus.FAILURE

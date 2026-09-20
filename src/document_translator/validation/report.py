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


@dataclass(frozen=True)
class DocumentValidationItem:
    location: str
    report: TranslationValidationReport


@dataclass(frozen=True)
class DocumentValidationReport:
    source_language: Language
    target_language: Language
    status: ValidationStatus
    items: tuple[DocumentValidationItem, ...]
    structural_issues: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return self.status is not ValidationStatus.FAILURE

    @property
    def failure_count(self) -> int:
        return sum(
            item.report.status is ValidationStatus.FAILURE
            for item in self.items
        ) + sum(
            issue.severity is ValidationStatus.FAILURE
            for issue in self.structural_issues
        )

    @property
    def warning_count(self) -> int:
        return sum(
            item.report.status is ValidationStatus.WARNING
            for item in self.items
        ) + sum(
            issue.severity is ValidationStatus.WARNING
            for issue in self.structural_issues
        )

    @property
    def pass_count(self) -> int:
        return sum(item.report.status is ValidationStatus.PASS for item in self.items)

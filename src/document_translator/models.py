"""Core domain models."""

from dataclasses import dataclass
from enum import StrEnum


class Language(StrEnum):
    ENGLISH = "en"
    HINDI = "hi"
    BENGALI = "bn"
    KANNADA = "kn"
    TELUGU = "te"
    TAMIL = "ta"
    MALAYALAM = "ml"


TARGET_LANGUAGES = frozenset(
    {
        Language.HINDI,
        Language.BENGALI,
        Language.KANNADA,
        Language.TELUGU,
        Language.TAMIL,
        Language.MALAYALAM,
    }
)


@dataclass(frozen=True)
class TranslationRequest:
    source_language: Language
    target_language: Language
    text: str


@dataclass(frozen=True)
class TranslationResult:
    source_language: Language
    target_language: Language
    source_text: str
    translated_text: str


@dataclass(frozen=True)
class TranslationFailure:
    source_language: Language
    target_language: Language
    source_text: str
    reason: str

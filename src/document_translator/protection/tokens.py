"""Protect and restore tokens that must not be translated."""

import re
from dataclasses import dataclass

_TOKEN_PATTERN = re.compile(
    r"(?:https?://\S+|www\.\S+|[\w.+-]+@[\w.-]+\.\w+|"
    r"\b(?:ORD|ID|REF)[-_][A-Z0-9-]+\b)"
)


@dataclass(frozen=True)
class ProtectedText:
    text: str
    tokens: dict[str, str]


def protect(text: str) -> ProtectedText:
    """Replace supported non-translatable tokens with stable placeholders."""
    tokens: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        placeholder = f"__DT_TOKEN_{len(tokens):04d}__"
        tokens[placeholder] = match.group(0)
        return placeholder

    return ProtectedText(_TOKEN_PATTERN.sub(replace, text), tokens)


def restore(text: str, tokens: dict[str, str]) -> str:
    """Restore protected tokens after translation."""
    for placeholder, original in tokens.items():
        text = text.replace(placeholder, original)
    return text

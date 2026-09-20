"""Domain models for supported DOCX structures."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RunModel:
    text: str
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None


@dataclass(frozen=True)
class ParagraphModel:
    text: str
    style: str | None
    runs: tuple[RunModel, ...]


@dataclass(frozen=True)
class TableModel:
    rows: tuple[tuple[ParagraphModel, ...], ...]


@dataclass(frozen=True)
class DocumentModel:
    paragraphs: tuple[ParagraphModel, ...]
    tables: tuple[TableModel, ...]

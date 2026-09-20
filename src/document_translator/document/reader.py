"""Read supported structures from DOCX files."""

from pathlib import Path

from docx import Document
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P

from document_translator.document.model import (
    DocumentBlock,
    DocumentModel,
    ParagraphModel,
    RunModel,
    TableModel,
)


def _paragraph_model(paragraph: Paragraph) -> ParagraphModel:
    return ParagraphModel(
        text=paragraph.text,
        style=paragraph.style.name if paragraph.style is not None else None,
        runs=tuple(
            RunModel(
                text=run.text,
                bold=run.bold,
                italic=run.italic,
                underline=run.underline,
            )
            for run in paragraph.runs
        ),
    )


def _table_model(table: Table) -> TableModel:
    return TableModel(
        rows=tuple(
            tuple(
                tuple(_paragraph_model(paragraph) for paragraph in cell.paragraphs)
                for cell in row.cells
            )
            for row in table.rows
        )
    )


def _body_blocks(document: Document) -> tuple[DocumentBlock, ...]:
    blocks: list[DocumentBlock] = []
    for element in document.element.body.iterchildren():
        if isinstance(element, CT_P):
            blocks.append(_paragraph_model(Paragraph(element, document)))
        elif isinstance(element, CT_Tbl):
            blocks.append(_table_model(Table(element, document)))
    return tuple(blocks)


def read_docx(path: str | Path) -> DocumentModel:
    """Read supported paragraphs, headings, runs, and tables from DOCX."""
    document = Document(path)
    return DocumentModel(blocks=_body_blocks(document))

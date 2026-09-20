"""Write supported document structures to DOCX files."""

from pathlib import Path

from docx import Document
from docx.table import _Cell
from docx.text.paragraph import Paragraph

from document_translator.document.model import (
    DocumentBlock,
    DocumentModel,
    ParagraphModel,
    TableModel,
)


def _write_paragraph(container, paragraph_model: ParagraphModel) -> Paragraph:
    paragraph = container.add_paragraph(style=paragraph_model.style)
    for run_model in paragraph_model.runs:
        run = paragraph.add_run(run_model.text)
        run.bold = run_model.bold
        run.italic = run_model.italic
        run.underline = run_model.underline
    return paragraph


def _write_cell(cell: _Cell, paragraph_model: ParagraphModel) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    for run_model in paragraph_model.runs:
        run = paragraph.add_run(run_model.text)
        run.bold = run_model.bold
        run.italic = run_model.italic
        run.underline = run_model.underline


def _write_table(document: Document, table_model: TableModel) -> None:
    row_count = len(table_model.rows)
    column_count = max((len(row) for row in table_model.rows), default=0)
    table = document.add_table(rows=row_count, cols=column_count)

    for row_index, row_model in enumerate(table_model.rows):
        for column_index, cell_paragraphs in enumerate(row_model):
            cell = table.cell(row_index, column_index)
            for paragraph_model in cell_paragraphs:
                _write_cell(cell, paragraph_model)


def write_docx(document_model: DocumentModel, path: str | Path) -> None:
    """Write a DocumentModel to a DOCX file."""
    document = Document()

    for block in document_model.blocks:
        if isinstance(block, ParagraphModel):
            _write_paragraph(document, block)
        elif isinstance(block, TableModel):
            _write_table(document, block)

    document.save(path)

# Document Translator

A Python application for translating English documents into Hindi, Bengali, Kannada, Telugu, Tamil, and Malayalam while preserving document structure and protecting non-translatable content.

## Current phase
Phase 2 adds the DOCX engine: structure-aware reading and reconstruction of paragraphs, headings, runs, and tables, with Unicode and round-trip tests.

See `ROADMAP.md` and `TODO.md` for the implementation plan.

## Development
Requires Python 3.11+.

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

# Document Translator

A Python application for translating English documents into Hindi, Bengali, Kannada, Telugu, Tamil, and Malayalam while preserving document structure and protecting non-translatable content.

## Current phase
Phase 1 establishes the engineering foundation: language registry, domain models, translation-provider contract, token protection, tests, Ruff, and CI.

See `ROADMAP.md` and `TODO.md` for the implementation plan.

## Development
Requires Python 3.11+.

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

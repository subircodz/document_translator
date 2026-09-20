# Document Translator

A Python application for translating English documents into Hindi, Bengali, Kannada, Telugu, Tamil, and Malayalam while preserving document structure and protecting non-translatable content.

## Current phase
Phase 3 adds the translation engine foundation: a Google Cloud Translation adapter, bounded batching, transient-failure retries, provider errors, and token protection around provider calls.

The current document pipeline is:

DOCX -> DocumentModel -> TranslationService -> TranslationProvider -> translated DocumentModel -> DOCX

See ROADMAP.md and TODO.md for the implementation plan.

## Google Cloud Translation

The first production provider is Google Cloud Translation Basic API (v2). The adapter reads GOOGLE_TRANSLATE_API_KEY from the environment unless an API key is passed directly to the provider.

Google Cloud currently documents Hindi, Bengali, Kannada, Telugu, Tamil, and Malayalam as supported translation languages. The adapter intentionally accepts only English-to-one-of-those-six target languages.

Do not commit API keys. Use environment variables or a secrets manager.

## Development

Requires Python 3.11+.

    python -m pip install -e ".[dev]"
    pytest
    ruff check .

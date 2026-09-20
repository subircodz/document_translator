# Document Translator

A Python application for translating English documents into Hindi, Bengali, Kannada, Telugu, Tamil, and Malayalam while preserving document structure and protecting non-translatable content.

## Current phase
Phase 7 begins production hardening of the FastAPI web application with DOCX upload, multi-language selection, background job progress, translated-document downloads, and validation-report downloads.

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

## Run the web application

Install development dependencies:

    python -m pip install -e ".[dev]"

Set the Google Cloud API key:

    export GOOGLE_TRANSLATE_API_KEY="your-key"

Start the application:

    uvicorn document_translator.web.app:app --reload

Open http://127.0.0.1:8000 in a browser.

The current web layer uses process-local jobs and temporary files. Phase 7 is hardening configuration, logging, limits, security, dependencies, performance, and release automation.

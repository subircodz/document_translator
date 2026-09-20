# Document Translator

A Python application for translating English DOCX documents into six Indian languages:

- Hindi (`hi`)
- Bengali (`bn`)
- Kannada (`kn`)
- Telugu (`te`)
- Tamil (`ta`)
- Malayalam (`ml`)

The application translates supported DOCX content through Google Cloud Translation, protects values that should not be translated, rebuilds the document, and validates the generated DOCX before exposing it for download.

## Supported workflow

```text
English DOCX
    |
    v
DOCX reader
    |
    v
DocumentModel
    |
    v
Protect URLs / emails / IDs / numbers
    |
    v
TranslationService
    |
    v
Google Cloud Translation
    |
    v
Restore protected tokens
    |
    v
Translated DocumentModel
    |
    +----> Validation
    |
    v
Translated DOCX + validation report
```

## Supported DOCX content

The current document model supports:

- paragraphs
- headings and paragraph styles
- multiple runs
- bold, italic, and underline run formatting
- tables
- multiple paragraphs inside table cells
- document order preservation for supported paragraphs and tables
- Unicode text, including the six target Indian scripts

The application does **not** guarantee preservation of every Microsoft Word feature. Images, headers/footers, hyperlinks, tracked changes, comments, embedded objects, and arbitrary section/page properties are outside the current document model.

## Requirements

- Python 3.11+
- Google Cloud account
- Cloud Translation API enabled
- Google Cloud Translation API key
- DOCX input

The current provider is Google Cloud Translation Basic API v2.

## Installation

```bash
git clone https://github.com/subircodz/document_translator.git
cd document_translator
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Configure Google Cloud Translation

Linux/macOS:

```bash
export GOOGLE_TRANSLATE_API_KEY="your-api-key"
```

Windows PowerShell:

```powershell
$env:GOOGLE_TRANSLATE_API_KEY="your-api-key"
```

Never commit the API key.

## Run locally

For development:

```bash
uvicorn document_translator.web.app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

For a controlled production deployment, do **not** use `--reload`:

```bash
uvicorn document_translator.web.app:app --host 0.0.0.0 --port 8000
```

Put the service behind HTTPS and a network boundary/reverse proxy when it is reachable by other users.

## Production web authentication

The application supports HTTP Basic authentication. For a production deployment, configure both variables:

```bash
export DOCUMENT_TRANSLATOR_WEB_USERNAME="translator"
export DOCUMENT_TRANSLATOR_WEB_PASSWORD="use-a-long-random-password"
```

If one is set without the other, application configuration fails.

The `/health` endpoint remains unauthenticated so a load balancer or process supervisor can check service health.

FastAPI's HTTP Basic support is based on the standard Authorization header and browser authentication prompt. citeturn0search0

## Production resource controls

The web service has these configurable controls:

| Variable | Default | Purpose |
|---|---:|---|
| `GOOGLE_TRANSLATE_API_KEY` | required | Google Translation API key |
| `DOCUMENT_TRANSLATOR_MAX_UPLOAD_BYTES` | `10485760` | Maximum upload: 10 MiB |
| `DOCUMENT_TRANSLATOR_MAX_ARCHIVE_UNCOMPRESSED_BYTES` | `104857600` | Maximum expanded DOCX archive: 100 MiB |
| `DOCUMENT_TRANSLATOR_JOB_TTL_SECONDS` | `3600` | Completed/failed job retention |
| `DOCUMENT_TRANSLATOR_MAX_CONCURRENT_JOBS` | `2` | Maximum queued/running jobs |
| `DOCUMENT_TRANSLATOR_RATE_LIMIT_REQUESTS` | `120` | Requests allowed per client per window |
| `DOCUMENT_TRANSLATOR_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window |
| `DOCUMENT_TRANSLATOR_WEB_USERNAME` | unset | Web username |
| `DOCUMENT_TRANSLATOR_WEB_PASSWORD` | unset | Web password |

Example production configuration:

```bash
export GOOGLE_TRANSLATE_API_KEY="your-api-key"
export DOCUMENT_TRANSLATOR_WEB_USERNAME="translator"
export DOCUMENT_TRANSLATOR_WEB_PASSWORD="use-a-long-random-password"
export DOCUMENT_TRANSLATOR_MAX_UPLOAD_BYTES="10485760"
export DOCUMENT_TRANSLATOR_MAX_ARCHIVE_UNCOMPRESSED_BYTES="104857600"
export DOCUMENT_TRANSLATOR_JOB_TTL_SECONDS="3600"
export DOCUMENT_TRANSLATOR_MAX_CONCURRENT_JOBS="2"
export DOCUMENT_TRANSLATOR_RATE_LIMIT_REQUESTS="120"
export DOCUMENT_TRANSLATOR_RATE_LIMIT_WINDOW_SECONDS="60"
```

The application also validates the DOCX ZIP archive before parsing it and rejects malformed, corrupt, over-large, or excessively populated archives.

## Using the web interface

1. Open the application.
2. Select an English `.docx`.
3. Select one or more target languages.
4. Click **Start translation**.
5. Wait for the status page to finish.
6. Download the translated DOCX.
7. Download the validation report.

Multiple target languages can be processed in one job.

## CLI

Translate one target language:

```bash
document-translator report.docx --target hi
```

Specify an output:

```bash
document-translator report.docx --target ta --output report.tamil.docx
```

The CLI now validates the generated DOCX and creates a report automatically:

```text
report.tamil.docx
report.tamil.report.txt
```

Specify a custom report:

```bash
document-translator report.docx --target ta --output report.tamil.docx --report validation.txt
```

The CLI exits with a failure when document validation reports a failure.

## Target languages

| Language | Code |
|---|---|
| Hindi | `hi` |
| Bengali | `bn` |
| Kannada | `kn` |
| Telugu | `te` |
| Tamil | `ta` |
| Malayalam | `ml` |

## Translation protection

Before text is sent to Google Cloud Translation, supported non-translatable values are protected.

Examples:

```text
https://example.com/orders/123
user@example.com
ORD-ABC-12345
1,250.50
25%
__CUSTOM_PLACEHOLDER__
```

The values are restored after translation and the validation layer checks for missing protected values and leaked internal placeholders.

## Validation

Every web translation is written to DOCX, read back, and validated before its download link is exposed.

Validation checks include:

- missing translation
- unchanged translation warnings
- invalid Unicode
- Unicode replacement characters
- missing protected tokens
- leaked placeholders
- document block count
- block types
- table row/cell/paragraph structure
- paragraph-level translation validation

Results are:

- `PASS`
- `WARNING`
- `FAILURE`

A warning requires review but is not automatically a failed document.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/` | Web upload page |
| `POST` | `/translate` | Upload/start job |
| `GET` | `/jobs/{job_id}` | Human-readable status |
| `GET` | `/api/translations/{job_id}` | JSON status |
| `GET` | `/api/translations/{job_id}/files/{target}` | Translated DOCX |
| `GET` | `/api/translations/{job_id}/reports/{target}` | Validation report |

## Architecture

```text
Web / CLI
   |
   v
Document translation orchestration
   |
   +--> DOCX reader/writer
   |
   +--> TranslationService
             |
             +--> token protection
             |
             +--> TranslationProvider
                       |
                       +--> Google Cloud adapter
```

The translation provider is isolated behind a provider contract so another provider can be added without rewriting the document layer.

## Operational model

Version 0.5.0 is production-ready for a **controlled single-instance deployment**.

The web job store is intentionally process-local and generated files are temporary. Therefore:

- run one application instance
- do not use multiple unsynchronized FastAPI workers
- put the service behind HTTPS and a trusted network boundary
- configure web authentication
- keep the Google API key in a secret store/environment
- monitor disk space and process health
- use `/health` for service checks

This release is **not a distributed multi-instance service**. A future distributed deployment would require persistent job storage, durable object storage, a worker queue, shared job state, and coordinated rate limiting.

## Testing

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
python -m build
```

GitHub Actions tests Python 3.11, 3.12, and 3.13, runs Ruff and pytest, builds distributions, and verifies that the built wheel can be installed and exposes the CLI.

## Release

Current release version:

```text
0.5.0
```

Create a release tag only after the main CI workflow is green:

```bash
git tag v0.5.0
git push origin v0.5.0
```

The release workflow independently runs Ruff, pytest, builds the wheel/source distribution, and verifies the built wheel before uploading the distributions as GitHub Actions artifacts. It does not publish automatically to PyPI.

## Project structure

```text
document_translator/
├── src/document_translator/
│   ├── cli.py
│   ├── config.py
│   ├── logging.py
│   ├── models.py
│   ├── document/
│   ├── protection/
│   ├── translation/
│   ├── validation/
│   └── web/
├── tests/
├── .github/workflows/
├── ROADMAP.md
├── TODO.md
├── pyproject.toml
└── README.md
```

## License

No open-source license has been declared. Until a license is added, treat the repository as private project code and do not redistribute it.

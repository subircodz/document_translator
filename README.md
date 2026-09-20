# Document Translator

A Python application that translates English DOCX documents into six major Indian languages:

- Hindi (`hi`)
- Bengali (`bn`)
- Kannada (`kn`)
- Telugu (`te`)
- Tamil (`ta`)
- Malayalam (`ml`)

The application is designed to translate document content while keeping the supported DOCX structure intact and protecting values that should not be translated, such as URLs, email addresses, identifiers, numbers, and placeholders.

## What the application does

The current application supports:

1. Upload an English `.docx` document.
2. Select one or more target languages.
3. Read the document structure.
4. Protect non-translatable tokens.
5. Translate the document text through Google Cloud Translation.
6. Rebuild the translated DOCX.
7. Validate the generated document against the source structure.
8. Download the translated DOCX and a validation report.
9. Track translation progress for each selected language.

Current supported flow:

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
Protect URLs / emails / IDs / numbers / placeholders
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

## Supported document content

The current DOCX engine supports:

- paragraphs
- headings and paragraph styles
- multiple runs
- bold, italic, and underline run formatting
- tables
- multiple paragraphs inside table cells
- document order preservation for supported paragraphs and tables
- Unicode text, including the six target Indian scripts

The application does **not** currently guarantee preservation of every feature supported by Microsoft Word. In particular, advanced layout/features such as images, headers/footers, hyperlinks, tracked changes, comments, embedded objects, and arbitrary section/page properties are outside the current document model.

## Requirements

- Python 3.11 or newer
- A Google Cloud account with Cloud Translation enabled
- A Google Cloud Translation API key
- A DOCX input file

The project currently uses Google Cloud Translation Basic API v2 as its translation provider.

## Installation

Clone the repository and enter the project directory:

```bash
git clone https://github.com/subircodz/document_translator.git
cd document_translator
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the application with development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Configure Google Cloud Translation

Set the API key as an environment variable.

Linux/macOS:

```bash
export GOOGLE_TRANSLATE_API_KEY="your-api-key"
```

Windows PowerShell:

```powershell
$env:GOOGLE_TRANSLATE_API_KEY="your-api-key"
```

Do **not** put the API key in source code, commit it to Git, or place it in the README.

## Run the web application

Start the FastAPI application:

```bash
uvicorn document_translator.web.app:app --reload
```

The application will normally be available at:

```text
http://127.0.0.1:8000
```

Open that address in a browser.

### Using the web interface

1. Open the application in your browser.
2. Select an English `.docx` file.
3. Select one or more target languages.
4. Click **Start translation**.
5. The application creates a translation job.
6. The status page shows progress.
7. When processing finishes, download the translated DOCX.
8. Download the validation report if you want to inspect structural and translation checks.

You can translate the same source document into multiple languages in one job.

## Command-line usage

The project also provides a CLI entry point:

```bash
document-translator INPUT.docx --target hi
```

Example:

```bash
document-translator report.docx --target ta
```

Specify the output path explicitly:

```bash
document-translator report.docx --target ta --output report.tamil.docx
```

The CLI currently accepts one target language per invocation.

Supported target codes:

| Language | Code |
|---|---|
| Hindi | `hi` |
| Bengali | `bn` |
| Kannada | `kn` |
| Telugu | `te` |
| Tamil | `ta` |
| Malayalam | `ml` |

If `--output` is omitted, the CLI creates a name based on the input and target language, for example:

```text
report.ta.docx
```

## Environment configuration

The web application supports these environment variables:

| Variable | Default | Purpose |
|---|---:|---|
| `GOOGLE_TRANSLATE_API_KEY` | required | Google Cloud Translation API key |
| `DOCUMENT_TRANSLATOR_MAX_UPLOAD_BYTES` | `10485760` | Maximum uploaded file size: 10 MiB |
| `DOCUMENT_TRANSLATOR_MAX_ARCHIVE_UNCOMPRESSED_BYTES` | `104857600` | Maximum total uncompressed DOCX ZIP size: 100 MiB |
| `DOCUMENT_TRANSLATOR_JOB_TTL_SECONDS` | `3600` | Lifetime of completed/failed jobs: 1 hour |

Example:

```bash
export GOOGLE_TRANSLATE_API_KEY="your-api-key"
export DOCUMENT_TRANSLATOR_MAX_UPLOAD_BYTES="10485760"
export DOCUMENT_TRANSLATOR_MAX_ARCHIVE_UNCOMPRESSED_BYTES="104857600"
export DOCUMENT_TRANSLATOR_JOB_TTL_SECONDS="3600"
```

## Translation protection

Before text is sent to the translation provider, the application detects and protects values that should normally remain unchanged.

Examples include:

```text
https://example.com/orders/123
user@example.com
ORD-ABC-12345
1,250.50
25%
__CUSTOM_PLACEHOLDER__
```

These values are replaced by internal placeholders during translation and restored afterward.

The validation layer then checks that protected values were not lost and that internal placeholders did not leak into the final document.

## Validation

Every web translation is validated after the output DOCX is written and read back.

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

The web application makes the validation report available as a text file next to the translated document.

A validation result can be:

- `PASS`
- `WARNING`
- `FAILURE`

A warning does not automatically mean the document is unusable. It means the validator found something that should be reviewed.

## API endpoints

The FastAPI application currently exposes:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Web upload page |
| `POST` | `/translate` | Upload and start a translation job |
| `GET` | `/jobs/{job_id}` | Human-readable job status page |
| `GET` | `/api/translations/{job_id}` | Job status as JSON |
| `GET` | `/api/translations/{job_id}/files/{target}` | Download translated DOCX |
| `GET` | `/api/translations/{job_id}/reports/{target}` | Download validation report |

## Application architecture

The project deliberately separates document processing from the translation provider.

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

This allows another translation provider to be added without rewriting the DOCX processing layer.

## Running tests and checks

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest
```

Run Ruff:

```bash
ruff check .
```

The GitHub Actions CI matrix tests Python 3.11, 3.12, and 3.13.

Dependency security auditing is also configured through GitHub Actions, and Dependabot is configured for Python and GitHub Actions dependencies.

## Release builds

Release builds are triggered by a Git tag matching:

```text
v*
```

For example:

```bash
git tag v0.4.0
git push origin v0.4.0
```

The release workflow builds the Python source distribution and wheel and stores them as GitHub Actions artifacts.

The release workflow does not publish to PyPI automatically.

## Production notes

The current web application is suitable as a controlled internal application or development deployment, but it is **not yet a fully distributed production service**.

Important current limitations:

- job state is process-local
- uploaded/generated files are stored in temporary directories
- there is no user authentication
- there is no persistent job database
- there is no distributed task queue
- there is no rate limiting
- a single FastAPI process owns the in-memory job store
- advanced DOCX features are not preserved by the current document model

For a larger deployment, the next engineering steps would include persistent job storage, a worker/task queue, authentication/authorization, rate limiting, centralized logging, object storage, and stronger deployment controls.

## Project structure

```text
document_translator/
├── src/document_translator/
│   ├── cli.py
│   ├── config.py
│   ├── logging.py
│   ├── models.py
│   ├── document/
│   │   ├── model.py
│   │   ├── reader.py
│   │   └── writer.py
│   ├── protection/
│   │   └── tokens.py
│   ├── translation/
│   │   ├── document.py
│   │   ├── errors.py
│   │   ├── google_cloud.py
│   │   ├── provider.py
│   │   └── service.py
│   ├── validation/
│   │   ├── report.py
│   │   ├── renderer.py
│   │   └── validator.py
│   └── web/
│       └── app.py
├── tests/
├── .github/workflows/
├── ROADMAP.md
├── TODO.md
├── pyproject.toml
└── README.md
```

## Project status

The implementation has completed the planned foundation, DOCX engine, translation engine, validation/reporting, CLI, web application, and current production-hardening work.

See:

- `ROADMAP.md` for the phase-by-phase development plan.
- `TODO.md` for the active engineering checklist.

## License

No open-source license has been declared yet. Until a license is added, treat the repository as private project code and do not redistribute it.

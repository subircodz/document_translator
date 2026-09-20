# Document Translator

Translate an English Microsoft Word document (DOCX) into **Hindi, Bengali, Kannada, Telugu, Tamil, or Malayalam**.

This README is the **client/user guide**: it explains what the application does, what is required, how to install and run it, and how to translate documents.

---

## 1. What this application does

The application takes an English `.docx` file and creates a translated `.docx` file.

```text
English DOCX
     |
     v
Upload document
     |
     v
Choose target language(s)
     |
     v
Google Cloud Translation
     |
     v
Translated DOCX
     |
     v
Validation report
```

The application also protects common values that should not be translated, such as:

- URLs
- email addresses
- IDs and codes
- numbers
- percentages
- placeholders

The generated document is validated before it is made available for download.

---

## 2. Supported languages

| Language | Code |
|---|---|
| Hindi | `hi` |
| Bengali | `bn` |
| Kannada | `kn` |
| Telugu | `te` |
| Tamil | `ta` |
| Malayalam | `ml` |

The source document is currently expected to be **English**.

---

## 3. Requirements

Before using the application, you need:

1. Python **3.11 or newer**
2. A Google Cloud account
3. Google Cloud Translation API enabled
4. A Google Cloud Translation API key
5. An English `.docx` document

The application currently uses **Google Cloud Translation Basic API v2**.

### Google API key

Set the API key as an environment variable.

**Linux/macOS**

```bash
export GOOGLE_TRANSLATE_API_KEY="your-api-key"
```

**Windows PowerShell**

```powershell
$env:GOOGLE_TRANSLATE_API_KEY="your-api-key"
```

**Important:** Never put the API key in the source code or commit it to GitHub.

---

# 4. Installation

Open a terminal and run:

```bash
git clone https://github.com/subircodz/document_translator.git
cd document_translator

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows PowerShell, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Then configure the Google API key as described above.

---

# 5. Start the application

## Local/development use

Run:

```bash
uvicorn document_translator.web.app:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

## Production use

For production, **do not use `--reload`**.

```bash
uvicorn document_translator.web.app:app --host 0.0.0.0 --port 8000
```

If the service is accessible to other users, place it behind HTTPS and a trusted reverse proxy/network boundary.

---

# 6. Using the web application

This is the normal way for a client/user to use the application.

### Step 1 — Open the application

Open:

```text
http://127.0.0.1:8000
```

### Step 2 — Select the document

Choose the English Word document (`.docx`) you want to translate.

### Step 3 — Select the language

Choose one or more target languages:

- Hindi
- Bengali
- Kannada
- Telugu
- Tamil
- Malayalam

### Step 4 — Start translation

Click **Start translation**.

The application creates a translation job and processes the selected languages.

### Step 5 — Wait for completion

Wait until the job finishes.

Do not stop the application while a translation is running.

### Step 6 — Download the translated document

Download the generated `.docx` file.

### Step 7 — Download the validation report

Download the validation report and review it before delivering the translated document.

---

# 7. Understanding the validation result

The application can return three validation states.

| Result | Meaning |
|---|---|
| **PASS** | The generated document passed the validation checks. |
| **WARNING** | The document was generated, but something should be reviewed. |
| **FAILURE** | The generated document failed a validation check. |

Validation checks include:

- missing translated text
- invalid Unicode
- Unicode replacement characters
- missing protected values
- leaked internal placeholders
- document structure
- paragraph structure
- table structure
- translation-level checks

A **WARNING** does not automatically mean the document is unusable. Review the validation report.

---

# 8. Supported Word formatting

The application currently supports:

- normal paragraphs
- headings
- paragraph styles
- multiple text runs
- **bold**
- *italic*
- underline
- tables
- multiple paragraphs inside table cells
- document order
- Unicode text

### Word features not guaranteed

The application does **not** guarantee preservation of every Microsoft Word feature.

The current document model does not guarantee preservation of:

- images
- headers and footers
- hyperlinks
- tracked changes
- comments
- embedded objects
- arbitrary section/page properties

If a document depends heavily on these features, inspect the translated DOCX before delivering it.

---

# 9. Example: translate a document

Suppose the input file is:

```text
report.docx
```

To create a Tamil translation:

```bash
document-translator report.docx --target ta --output report.tamil.docx
```

The application produces:

```text
report.tamil.docx
report.tamil.report.txt
```

- `report.tamil.docx` — translated Word document
- `report.tamil.report.txt` — validation report

---

# 10. Command-line usage

The web interface is recommended for normal users, but the application also provides a CLI.

### Hindi

```bash
document-translator report.docx --target hi
```

### Bengali

```bash
document-translator report.docx --target bn
```

### Kannada

```bash
document-translator report.docx --target kn
```

### Telugu

```bash
document-translator report.docx --target te
```

### Tamil

```bash
document-translator report.docx --target ta
```

### Malayalam

```bash
document-translator report.docx --target ml
```

### Custom output filename

```bash
document-translator report.docx \
  --target ta \
  --output report.tamil.docx
```

### Custom validation report

```bash
document-translator report.docx \
  --target ta \
  --output report.tamil.docx \
  --report validation.txt
```

The CLI validates the generated DOCX. If validation reports a failure, the command exits with a failure status.

---

# 11. Production security

For a production deployment, configure web login protection:

```bash
export DOCUMENT_TRANSLATOR_WEB_USERNAME="translator"
export DOCUMENT_TRANSLATOR_WEB_PASSWORD="use-a-long-random-password"
```

Configure **both** variables.

If only one is configured, application configuration fails.

The `/health` endpoint remains available without authentication so a process supervisor or load balancer can check service health.

Health check:

```text
/health
```

Expected response:

```json
{"status":"ok"}
```

---

# 12. Production configuration

These environment variables can be configured:

| Variable | Default | Purpose |
|---|---:|---|
| `GOOGLE_TRANSLATE_API_KEY` | Required | Google Translation API key |
| `DOCUMENT_TRANSLATOR_WEB_USERNAME` | Not set | Web login username |
| `DOCUMENT_TRANSLATOR_WEB_PASSWORD` | Not set | Web login password |
| `DOCUMENT_TRANSLATOR_MAX_UPLOAD_BYTES` | `10485760` | Maximum upload size: 10 MiB |
| `DOCUMENT_TRANSLATOR_MAX_ARCHIVE_UNCOMPRESSED_BYTES` | `104857600` | Maximum expanded DOCX archive: 100 MiB |
| `DOCUMENT_TRANSLATOR_JOB_TTL_SECONDS` | `3600` | Retention time for completed/failed jobs |
| `DOCUMENT_TRANSLATOR_MAX_CONCURRENT_JOBS` | `2` | Maximum queued/running jobs |
| `DOCUMENT_TRANSLATOR_RATE_LIMIT_REQUESTS` | `120` | Requests allowed per client |
| `DOCUMENT_TRANSLATOR_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window in seconds |

Example:

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

---

# 13. Important deployment limitation

Version 0.5.0 is designed for a **controlled single-instance deployment**.

The web job state is kept in the running application process and generated files are temporary.

Therefore:

- run one application instance
- do not run multiple unsynchronized application workers
- keep the Google API key in environment variables or a secret manager
- use HTTPS when users access the service over a network
- monitor disk space and application health

This release is **not a distributed multi-instance service**.

A future distributed deployment would require persistent job storage, durable file storage, a worker queue, shared job state, and coordinated rate limiting.

---

# 14. What happens to values that should not be translated?

Before text is sent to Google Cloud Translation, supported non-translatable values are protected.

For example:

```text
https://example.com/orders/123
user@example.com
ORD-ABC-12345
1,250.50
25%
__CUSTOM_PLACEHOLDER__
```

These values are restored after translation.

The validation layer checks that protected values were not lost and that internal placeholders were not left in the final document.

---

# 15. API endpoints

The application provides these endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Service health check |
| GET | `/` | Web application |
| POST | `/translate` | Start a translation job |
| GET | `/jobs/{job_id}` | Human-readable job status |
| GET | `/api/translations/{job_id}` | JSON job status |
| GET | `/api/translations/{job_id}/files/{target}` | Download translated DOCX |
| GET | `/api/translations/{job_id}/reports/{target}` | Download validation report |

Normal users do **not** need to call these endpoints directly. The web interface handles the normal workflow.

---

# 16. Troubleshooting

## API key is missing

Check that the API key is set in the same terminal/session where the application is started:

```bash
echo $GOOGLE_TRANSLATE_API_KEY
```

Then restart the application.

## Application does not start

Check Python:

```bash
python --version
```

Python 3.11 or newer is required.

Make sure the virtual environment is active:

```bash
source .venv/bin/activate
```

Then reinstall:

```bash
python -m pip install -e ".[dev]"
```

## Document is rejected

Check that:

- the file is a valid `.docx`
- the file is within the configured upload limit
- the DOCX archive is not corrupt
- the document does not depend on unsupported Word features

## Translation fails

Check:

1. Google Cloud Translation API is enabled.
2. The API key is correct.
3. The machine has network access to Google Cloud.
4. The Google Cloud project/API configuration allows the request.
5. The application logs for the actual error.

## Validation reports a warning

Download and read the validation report.

A warning means the document was generated but requires review.

---

# 17. Basic health check

After starting the application, open:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

This confirms that the application process is responding.

It does **not** by itself prove that a translation request will succeed; Google API configuration and credentials must also be valid.

---

# 18. Developer information

The project is organized into separate document, translation, protection, validation, CLI, and web layers.

```text
Web / CLI
   |
   v
Translation orchestration
   |
   +--> DOCX reader/writer
   |
   +--> TranslationService
           |
           +--> Token protection
           |
           +--> Translation provider
                    |
                    +--> Google Cloud adapter
```

The translation provider is isolated behind a provider contract so another provider can be introduced later without rewriting the document-processing layer.

---

# 19. Testing

For developers:

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
python -m build
```

The CI workflow tests Python 3.11, 3.12, and 3.13, runs Ruff and pytest, builds the package, and verifies installation of the built wheel.

---

# 20. Current release

**Version:** 0.5.0

This release is production-ready for the documented **controlled single-instance deployment model**.

It is not a distributed SaaS deployment.

---

## License

No open-source license has been declared.

Until a license is added, treat this repository as private project code and do not redistribute it.

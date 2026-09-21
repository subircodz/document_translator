"""FastAPI web application for document translation."""

from __future__ import annotations

import html
import io
import logging
import secrets
import threading
import time
import uuid
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from document_translator.config import ConfigurationError, Settings
from document_translator.document.reader import read_docx
from document_translator.document.writer import write_docx
from document_translator.logging import configure_logging
from document_translator.models import TARGET_LANGUAGES, Language
from document_translator.translation.document import translate_document
from document_translator.translation.google_cloud import GoogleCloudTranslationProvider
from document_translator.translation.service import TranslationService
from document_translator.validation.renderer import render_document_report
from document_translator.validation.validator import validate_document

_ALLOWED_SUFFIX = ".docx"
_MAX_DOCX_ENTRIES = 10000
_LOGGER = logging.getLogger(__name__)


@dataclass
class TargetOutput:
    target: Language
    document_path: Path | None = None
    report_path: Path | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    ttl_seconds: int = 3600


@dataclass
class TranslationJob:
    job_id: str
    source_name: str
    targets: tuple[Language, ...]
    work_dir: Path
    temp_dir: TemporaryDirectory[str]
    status: str = "queued"
    progress: int = 0
    outputs: dict[str, TargetOutput] = field(default_factory=dict)
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    ttl_seconds: int = 3600

    def cleanup(self) -> None:
        self.temp_dir.cleanup()


class JobStore:
    """Process-local job store for a single-instance deployment."""

    def __init__(self) -> None:
        self._jobs: dict[str, TranslationJob] = {}
        self._lock = threading.Lock()

    def add(self, job: TranslationJob) -> None:
        with self._lock:
            self._jobs[job.job_id] = job

    def get(self, job_id: str) -> TranslationJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if (
                job is not None
                and job.status not in {"queued", "running"}
                and time.time() - job.created_at > job.ttl_seconds
            ):
                self._jobs.pop(job_id, None)
                job.cleanup()
                return None
            return job

    def active_count(self) -> int:
        with self._lock:
            return sum(
                job.status in {"queued", "running"} for job in self._jobs.values()
            )


STORE = JobStore()


def _parse_targets(values: list[str]) -> tuple[Language, ...]:
    if not values:
        raise HTTPException(status_code=400, detail="Select at least one target language.")
    targets: list[Language] = []
    for value in values:
        try:
            language = Language(value.lower())
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"Unsupported target language: {value}"
            ) from exc
        if language not in TARGET_LANGUAGES:
            raise HTTPException(
                status_code=400, detail=f"Unsupported target language: {value}"
            )
        if language not in targets:
            targets.append(language)
    return tuple(targets)


def _safe_source_name(filename: str | None) -> str:
    name = Path(filename or "document.docx").name
    if not name or Path(name).suffix.lower() != _ALLOWED_SUFFIX:
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")
    return name


def _validate_docx_archive(data: bytes, max_uncompressed_bytes: int) -> None:
    """Reject malformed, oversized, or suspicious DOCX ZIP payloads before parsing."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if len(archive.infolist()) > _MAX_DOCX_ENTRIES:
                raise HTTPException(
                    status_code=400,
                    detail="DOCX contains too many archive entries.",
                )
            if archive.testzip() is not None:
                raise HTTPException(status_code=400, detail="DOCX archive is corrupt.")
            total_uncompressed = sum(
                info.file_size for info in archive.infolist()
            )
            if total_uncompressed > max_uncompressed_bytes:
                raise HTTPException(
                    status_code=413,
                    detail="DOCX expands beyond the configured archive limit.",
                )
    except zipfile.BadZipFile as exc:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not a valid DOCX archive.",
        ) from exc


def _run_job(
    job: TranslationJob,
    source_path: Path,
    api_key: str,
    provider_factory: Callable[[str], object],
) -> None:
    job.status = "running"
    _LOGGER.info(
        "translation_job_started job_id=%s targets=%s",
        job.job_id,
        [target.value for target in job.targets],
    )
    try:
        source = read_docx(source_path)
        service = TranslationService(provider_factory(api_key))
        total = len(job.targets)
        for index, target in enumerate(job.targets, start=1):
            try:
                translated = translate_document(source, service, target)
                output_path = job.work_dir / (
                    f"{Path(job.source_name).stem}.{target.value}.docx"
                )
                write_docx(translated, output_path)
                reloaded = read_docx(output_path)
                report = validate_document(
                    source, reloaded, Language.ENGLISH, target
                )
                report_path = job.work_dir / (
                    f"{Path(job.source_name).stem}.{target.value}.report.txt"
                )
                report_path.write_text(
                    render_document_report(report), encoding="utf-8"
                )
                job.outputs[target.value] = TargetOutput(
                    target, output_path, report_path
                )
            except (OSError, RuntimeError, ValueError) as exc:
                job.outputs[target.value] = TargetOutput(target, error=str(exc))
            job.progress = int(index * 100 / total)
            _LOGGER.info(
                "translation_target_finished job_id=%s target=%s progress=%s",
                job.job_id,
                target.value,
                job.progress,
            )
        if all(output.error is None for output in job.outputs.values()):
            job.status = "completed"
        else:
            job.status = "completed_with_errors"
        _LOGGER.info(
            "translation_job_finished job_id=%s status=%s",
            job.job_id,
            job.status,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        job.error = str(exc)
        job.status = "failed"
        _LOGGER.exception("translation_job_failed job_id=%s", job.job_id)


def _job_payload(job: TranslationJob) -> dict[str, object]:
    outputs = []
    for target, output in job.outputs.items():
        item: dict[str, object] = {"target": target, "error": output.error}
        if output.error is None:
            item["document_url"] = (
                f"/api/translations/{job.job_id}/files/{target}"
            )
            item["report_url"] = (
                f"/api/translations/{job.job_id}/reports/{target}"
            )
        outputs.append(item)
    return {
        "job_id": job.job_id,
        "source": job.source_name,
        "status": job.status,
        "progress": job.progress,
        "error": job.error,
        "outputs": outputs,
    }


def create_app(provider_factory=None, settings: Settings | None = None) -> FastAPI:
    """Create the web application with injectable provider and settings."""
    if provider_factory is None:
        provider_factory = lambda api_key: GoogleCloudTranslationProvider(
            api_key=api_key
        )
    if settings is None:
        try:
            settings = Settings.from_environment()
        except ConfigurationError:
            settings = None
    if settings is not None:
        configure_logging()

    app = FastAPI(title="Document Translator", version="0.5.0")
    rate_lock = threading.Lock()
    request_times: dict[str, list[float]] = {}

    @app.middleware("http")
    async def security_middleware(request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        if settings is None:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with rate_lock:
            recent = [
                timestamp
                for timestamp in request_times.get(client_host, [])
                if now - timestamp < settings.rate_limit_window_seconds
            ]
            if len(recent) >= settings.rate_limit_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                    headers={"Retry-After": str(settings.rate_limit_window_seconds)},
                )
            recent.append(now)
            request_times[client_host] = recent

        if settings.web_username and settings.web_password:
            authorization = request.headers.get("authorization", "")
            try:
                scheme, encoded = authorization.split(" ", 1)
                import base64

                decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
                username, password = decoded.split(":", 1)
            except (ValueError, UnicodeDecodeError, TypeError):
                username = password = ""
                scheme = ""

            if (
                scheme.lower() != "basic"
                or not secrets.compare_digest(username, settings.web_username)
                or not secrets.compare_digest(password, settings.web_password)
            ):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required."},
                    headers={"WWW-Authenticate": 'Basic realm="Document Translator"'},
                )

        return await call_next(request)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        languages = "".join(
            f'<label><input type="checkbox" name="targets" value="{lang.value}"> '
            f"{lang.name.title()}</label>"
            for lang in sorted(TARGET_LANGUAGES, key=lambda item: item.value)
        )
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Document Translator</title>
<style>body{{font-family:system-ui;max-width:760px;margin:40px auto;padding:0 20px}}
label{{display:block;margin:8px 0}}button{{margin-top:18px;padding:10px 18px}}
.hint{{color:#555}}</style></head><body><h1>Document Translator</h1>
<p class="hint">Translate an English DOCX into one or more Indian languages.</p>
<form action="/translate" method="post" enctype="multipart/form-data">
<p><input type="file" name="file" accept=".docx" required></p>
<fieldset><legend>Target languages</legend>{languages}</fieldset>
<button type="submit">Start translation</button></form></body></html>"""

    @app.post("/translate", response_class=HTMLResponse)
    async def translate_form(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),  # noqa: B008
        targets: list[str] = Form(...),  # noqa: B008
    ) -> str:
        job = await _create_job(file, targets, background_tasks)
        return f'<meta http-equiv="refresh" content="0; url=/jobs/{job.job_id}">'

    @app.get("/jobs/{job_id}", response_class=HTMLResponse)
    def job_page(job_id: str) -> str:
        job = STORE.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Translation job not found.")
        source_name = html.escape(job.source_name)
        return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Translation status</title><meta http-equiv="refresh" content="2">
<style>body{{font-family:system-ui;max-width:760px;margin:40px auto;padding:0 20px}}
li{{margin:12px 0}}</style></head><body><h1>Translation status</h1>
<p>File: {source_name}</p><p>Status: <strong>{job.status}</strong> — {job.progress}%</p>
<ul>{''.join(_html_output(job, target) for target in job.targets)}</ul></body></html>"""

    @app.get("/api/translations/{job_id}")
    def job_status(job_id: str) -> dict[str, object]:
        job = STORE.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Translation job not found.")
        return _job_payload(job)

    @app.get("/api/translations/{job_id}/files/{target}")
    def download_document(job_id: str, target: str) -> FileResponse:
        output = _get_output(job_id, target).document_path
        if output is None or not output.is_file():
            raise HTTPException(
                status_code=404, detail="Translated document is not available."
            )
        return FileResponse(
            output,
            filename=output.name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    @app.get("/api/translations/{job_id}/reports/{target}")
    def download_report(job_id: str, target: str) -> FileResponse:
        output = _get_output(job_id, target).report_path
        if output is None or not output.is_file():
            raise HTTPException(
                status_code=404, detail="Validation report is not available."
            )
        return FileResponse(
            output,
            filename=output.name,
            media_type="text/plain; charset=utf-8",
        )

    async def _create_job(
        file: UploadFile, target_values: list[str], background_tasks: BackgroundTasks
    ) -> TranslationJob:
        source_name = _safe_source_name(file.filename)
        targets_tuple = _parse_targets(target_values)
        if settings is None:
            raise HTTPException(
                status_code=503,
                detail="GOOGLE_TRANSLATE_API_KEY is not configured.",
            )
        if STORE.active_count() >= settings.max_concurrent_jobs:
            raise HTTPException(
                status_code=429,
                detail="Maximum concurrent translation jobs reached.",
                headers={"Retry-After": "30"},
            )

        api_key = settings.google_translate_api_key
        data = await file.read(settings.max_upload_bytes + 1)
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail="File exceeds the configured upload limit.",
            )
        _validate_docx_archive(data, settings.max_archive_uncompressed_bytes)
        work_dir_obj = TemporaryDirectory(prefix="document-translator-")
        work_dir = Path(work_dir_obj.name)
        source_path = work_dir / source_name
        source_path.write_bytes(data)
        job = TranslationJob(
            str(uuid.uuid4()),
            source_name,
            targets_tuple,
            work_dir,
            work_dir_obj,
            ttl_seconds=settings.job_ttl_seconds,
        )
        job.outputs = {
            target.value: TargetOutput(target) for target in targets_tuple
        }
        STORE.add(job)
        background_tasks.add_task(
            _run_job, job, source_path, api_key, provider_factory
        )
        return job

    return app


def _html_output(job: TranslationJob, target: Language) -> str:
    output = job.outputs.get(target.value)
    language_names = {
        "hi": "Hindi",
        "bn": "Bengali",
        "kn": "Kannada",
        "te": "Telugu",
        "ta": "Tamil",
        "ml": "Malayalam",
    }
    name = language_names.get(target.value, target.name.title())
    if output is None or output.error is not None:
        error = (
            html.escape(output.error)
            if output and output.error
            else "Waiting to start"
        )
        return (
            f'<article class="output"><div class="output-head"><span class="lang">'
            f'{name}</span><span class="pill">Pending</span></div>'
            f'<div class="error">{error}</div></article>'
        )
    return (
        f'<article class="output"><div class="output-head"><span class="lang">'
        f'{name}</span><span class="pill">Ready</span></div>'
        f'<div class="links"><a href="/api/translations/{job.job_id}/files/'
        f'{target.value}">Download DOCX</a><a class="secondary" href="/api/translations/'
        f'{job.job_id}/reports/{target.value}">Validation report</a></div></article>'
    )


def _get_output(job_id: str, target: str) -> TargetOutput:
    job = STORE.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Translation job not found.")
    try:
        language = Language(target.lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=404, detail="Target language not found."
        ) from exc
    output = job.outputs.get(language.value)
    if output is None:
        raise HTTPException(
            status_code=404, detail="Target language not found for this job."
        )
    return output


app = create_app()

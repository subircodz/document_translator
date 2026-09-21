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
        names = {"hi": "Hindi", "bn": "Bengali", "kn": "Kannada", "te": "Telugu", "ta": "Tamil", "ml": "Malayalam"}
        languages = "".join(
            f'<label class="lang"><input type="checkbox" name="targets" value="{lang.value}">'
            f'<span class="code">{lang.value.upper()}</span><span><b>{names.get(lang.value, lang.name.title())}</b>'
            f'<small>{lang.value.upper()} translation</small></span><i>✓</i></label>'
            for lang in sorted(TARGET_LANGUAGES, key=lambda item: item.value)
        )
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Document Translator</title>
<style>
:root{{--bg:#07111f;--card:#0e1d32;--text:#f6f8fb;--muted:#9caec5;--line:#ffffff18;--cyan:#69e6f7;--violet:#9b8cff}}
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;font-family:Inter,system-ui,sans-serif;color:var(--text);background:radial-gradient(circle at 15% 0,#163d58 0,transparent 32%),radial-gradient(circle at 90% 10%,#292253 0,transparent 34%),var(--bg)}}
.shell{{width:min(1000px,calc(100% - 32px));margin:auto;padding:32px 0 60px}}.nav{{display:flex;justify-content:space-between;align-items:center;margin-bottom:60px}}
.brand{{display:flex;gap:11px;align-items:center;font-weight:800;letter-spacing:-.02em}}.logo{{width:40px;height:40px;border-radius:12px;display:grid;place-items:center;background:linear-gradient(135deg,var(--cyan),var(--violet));color:#06101d;font-weight:900}}
.badge{{font-size:12px;color:var(--muted);border:1px solid var(--line);padding:7px 11px;border-radius:99px;background:#ffffff08}}
.hero{{text-align:center;max-width:760px;margin:auto auto 34px}}.eyebrow{{color:var(--cyan);font-size:12px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}}
h1{{font-size:clamp(42px,7vw,72px);line-height:1;letter-spacing:-.06em;margin:14px 0 18px}}.hero p{{color:var(--muted);font-size:18px;line-height:1.6}}
.panel{{background:#0e1d32dd;border:1px solid var(--line);border-radius:28px;padding:26px;box-shadow:0 28px 80px #0007;backdrop-filter:blur(16px)}}
.drop{{display:block;text-align:center;padding:36px 20px;border:1.5px dashed #69e6f755;border-radius:20px;cursor:pointer;background:#69e6f708;transition:.2s}}
.drop:hover,.drop.drag{{border-color:var(--cyan);background:#69e6f712}}.drop input{{display:none}}.icon{{font-size:28px;margin-bottom:10px}}.drop b{{display:block;font-size:17px}}.drop small{{display:block;color:var(--muted);margin-top:7px}}#file-name{{color:#62e3a5;font-size:13px;margin-top:12px;min-height:18px}}
.head{{display:flex;justify-content:space-between;align-items:end;margin:28px 0 13px}}.head h2{{font-size:16px;margin:0}}.head span{{font-size:12px;color:var(--muted)}}
.languages{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.lang{{position:relative;display:flex;align-items:center;gap:11px;padding:14px;border:1px solid var(--line);border-radius:16px;background:#ffffff05;cursor:pointer;transition:.2s}}
.lang:hover,.lang:has(input:checked){{border-color:#69e6f799;background:#69e6f70d}}.lang input{{position:absolute;opacity:0}}.code{{width:38px;height:38px;border-radius:11px;display:grid;place-items:center;background:#9b8cff18;color:#c9c1ff;font-size:11px;font-weight:900}}
.lang b{{display:block;font-size:14px}}.lang small{{display:block;color:var(--muted);font-size:10px;margin-top:3px}}.lang i{{margin-left:auto;color:var(--cyan);opacity:0;font-style:normal;font-weight:900}}.lang:has(input:checked) i{{opacity:1}}
.actions{{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-top:24px}}.hint{{color:var(--muted);font-size:12px}}button{{border:0;border-radius:14px;padding:14px 22px;font:inherit;font-weight:800;color:#06101d;background:linear-gradient(135deg,var(--cyan),#b3f7ff);cursor:pointer;box-shadow:0 12px 32px #69e6f72b}}button:disabled{{opacity:.45;cursor:not-allowed}}
footer{{text-align:center;color:#6e819b;font-size:12px;margin-top:20px}}@media(max-width:700px){{.languages{{grid-template-columns:1fr 1fr}}.actions{{flex-direction:column;align-items:stretch}}button{{width:100%}}}}@media(max-width:470px){{.languages{{grid-template-columns:1fr}}.shell{{width:min(100% - 20px,1000px)}}}}
</style></head><body><main class="shell">
<header class="nav"><div class="brand"><div class="logo">文</div>Document Translator</div><span class="badge">v0.5.0 · DOCX</span></header>
<section class="hero"><div class="eyebrow">Structure-aware document translation</div><h1>Translate once.<br><span style="background:linear-gradient(90deg,var(--cyan),#bdb4ff);-webkit-background-clip:text;color:transparent">Speak everywhere.</span></h1>
<p>Turn an English Word document into Hindi, Bengali, Kannada, Telugu, Tamil or Malayalam while keeping supported structure and formatting intact.</p></section>
<section class="panel"><form id="form" action="/translate" method="post" enctype="multipart/form-data">
<label class="drop" id="drop"><input id="file" type="file" name="file" accept=".docx" required><div class="icon">↑</div><b>Drop your DOCX here</b><small>or click to choose a file · maximum 10 MB</small><div id="file-name"></div></label>
<div class="head"><h2>Target languages</h2><span id="count">0 selected</span></div><div class="languages">{languages}</div>
<div class="actions"><span class="hint">Select one or more languages. Your translation starts as a background job.</span><button id="submit" type="submit" disabled>Start translation →</button></div>
</form></section><footer>URLs, emails and other protected identifiers are preserved during translation.</footer></main>
<script>
const f=document.getElementById("file"),d=document.getElementById("drop"),n=document.getElementById("file-name"),c=document.getElementById("count"),b=document.getElementById("submit");
function sync(){{const x=document.querySelectorAll('input[name="targets"]:checked').length;c.textContent=x+" selected";b.disabled=!f.files.length||!x}}
f.onchange=()=>{{n.textContent=f.files[0]?.name||"";sync()}};["dragenter","dragover"].forEach(x=>d.addEventListener(x,e=>{{e.preventDefault();d.classList.add("drag")}}));["dragleave","drop"].forEach(x=>d.addEventListener(x,e=>{{e.preventDefault();d.classList.remove("drag")}}));
d.addEventListener("drop",e=>{{if(e.dataTransfer.files.length){{f.files=e.dataTransfer.files;n.textContent=f.files[0].name;sync()}}}});document.querySelectorAll('input[name="targets"]').forEach(x=>x.onchange=sync);
document.getElementById("form").onsubmit=()=>{{b.disabled=true;b.textContent="Uploading…" }};sync();
</script></body></html>"""
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
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Translation · {source_name}</title><style>
:root{{--bg:#07111f;--card:#0e1d32dd;--text:#f5f8fb;--muted:#9caec5;--line:#ffffff18;--cyan:#69e6f7;--green:#61e5a5}}
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;font-family:Inter,system-ui,sans-serif;color:var(--text);background:radial-gradient(circle at 20% 0,#173b55 0,transparent 32%),radial-gradient(circle at 90% 20%,#292253 0,transparent 34%),var(--bg)}}.shell{{width:min(900px,calc(100% - 30px));margin:auto;padding:32px 0 60px}}
.top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:34px}}.brand{{display:flex;align-items:center;gap:10px;font-weight:800}}.logo{{width:36px;height:36px;border-radius:11px;display:grid;place-items:center;background:linear-gradient(135deg,var(--cyan),#9d8cff);color:#06101d}}.back{{color:var(--muted);text-decoration:none;font-size:13px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:25px;padding:27px;box-shadow:0 28px 80px #0007;backdrop-filter:blur(16px)}}.eyebrow{{color:var(--cyan);font-size:11px;font-weight:900;letter-spacing:.14em;text-transform:uppercase}}h1{{font-size:clamp(28px,5vw,44px);letter-spacing:-.045em;margin:9px 0}}.meta{{color:var(--muted);font-size:13px}}
.track{{height:10px;background:#ffffff0d;border-radius:99px;overflow:hidden;margin:27px 0 9px}}.bar{{height:100%;background:linear-gradient(90deg,var(--cyan),#9d8cff);border-radius:99px;transition:width .4s}}.row{{display:flex;justify-content:space-between;color:var(--muted);font-size:13px}}.row strong{{color:var(--text)}}
.outputs{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-top:22px}}.output{{padding:17px;border:1px solid var(--line);border-radius:17px;background:#ffffff04}}.output-head{{display:flex;justify-content:space-between;align-items:center;gap:10px}}.lang{{font-weight:850}}.pill{{font-size:10px;padding:5px 8px;border-radius:99px;color:var(--green);background:#61e5a512}}.links{{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}}.links a{{padding:8px 10px;border-radius:10px;text-decoration:none;background:var(--cyan);color:#06101d;font-size:11px;font-weight:850}}.links a.secondary{{color:var(--text);background:#ffffff0a;border:1px solid var(--line)}}.error{{color:#ff9bab;font-size:12px;margin-top:9px}}.note{{margin-top:18px;padding:12px 14px;border-radius:12px;color:var(--muted);background:#ffffff05;font-size:12px;line-height:1.5}}@media(max-width:620px){{.outputs{{grid-template-columns:1fr}}.card{{padding:20px}}}}
</style></head><body><main class="shell"><div class="top"><div class="brand"><div class="logo">文</div>Document Translator</div><a class="back" href="/">← Translate another</a></div>
<section class="card"><div class="eyebrow">Translation job</div><h1>{source_name}</h1><div class="meta">Job {job.job_id[:8]} · <span id="status">{html.escape(job.status.replace("_"," ").title())}</span></div>
<div class="track"><div class="bar" id="bar" style="width:{job.progress}%"></div></div><div class="row"><span id="state">{html.escape(job.status.replace("_"," ").title())}</span><strong id="pct">{job.progress}%</strong></div>
<div class="outputs" id="outputs">{''.join(_html_output(job, target) for target in job.targets)}</div><div class="note">This page checks job progress automatically. Completed targets can be downloaded immediately.</div>
</section></main><script>
const id="{job.job_id}";async function refresh(){{try{{const r=await fetch("/api/translations/"+id,{{cache:"no-store"}});if(!r.ok)return;const d=await r.json();document.getElementById("bar").style.width=d.progress+"%";document.getElementById("pct").textContent=d.progress+"%";const s=d.status.replaceAll("_"," ");document.getElementById("state").textContent=s[0].toUpperCase()+s.slice(1);document.getElementById("status").textContent=document.getElementById("state").textContent;if(d.status==="completed"||d.status==="completed_with_errors"||d.status==="failed")location.reload()}}catch(e){{}}}}setInterval(refresh,2000);
</script></body></html>"""
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

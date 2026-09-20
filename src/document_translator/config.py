"""Application configuration and environment validation."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    google_translate_api_key: str
    max_upload_bytes: int = 10 * 1024 * 1024
    job_ttl_seconds: int = 3600

    @classmethod
    def from_environment(cls) -> Settings:
        api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY", "").strip()
        if not api_key:
            raise ConfigurationError("GOOGLE_TRANSLATE_API_KEY is not configured.")
        return cls(
            google_translate_api_key=api_key,
            max_upload_bytes=_positive_int("DOCUMENT_TRANSLATOR_MAX_UPLOAD_BYTES", 10 * 1024 * 1024),
            job_ttl_seconds=_positive_int("DOCUMENT_TRANSLATOR_JOB_TTL_SECONDS", 3600),
        )


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a positive integer.") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be a positive integer.")
    return value

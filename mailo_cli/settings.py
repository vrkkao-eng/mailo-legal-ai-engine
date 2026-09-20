"""Explicit, conservative runtime settings for the HTTP service."""

import os
from dataclasses import dataclass


def _positive_int(name: str, default: int, maximum: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not 1 <= value <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return value


@dataclass(frozen=True)
class ApiSettings:
    max_request_bytes: int = 1_048_576
    request_timeout_seconds: int = 30
    cors_origins: tuple[str, ...] = ()


def load_api_settings() -> ApiSettings:
    origins = tuple(
        origin.strip()
        for origin in os.getenv("MAILO_CORS_ORIGINS", "").split(",")
        if origin.strip()
    )
    return ApiSettings(
        max_request_bytes=_positive_int("MAILO_MAX_REQUEST_BYTES", 1_048_576, 10_485_760),
        request_timeout_seconds=_positive_int("MAILO_REQUEST_TIMEOUT_SECONDS", 30, 300),
        cors_origins=origins,
    )

"""Structured, privacy-preserving observability for S34."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import re
import sys
import traceback
from typing import TextIO
import uuid


REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def safe_request_id(candidate: str | None) -> str:
    value = str(candidate or "")
    if REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid.uuid4().hex


def pseudonymous_user_ref(secret: str, user_id: object) -> str:
    digest = hmac.new(
        str(secret).encode("utf-8"),
        f"sammlr-user:{user_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest[:16]


def _write_json(stream: TextIO, payload: dict) -> None:
    stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    stream.flush()


def write_request_log(payload: dict, stream: TextIO | None = None) -> None:
    _write_json(stream or sys.stdout, payload)


class ErrorTracker:
    """Provider-neutral boundary for unexpected technical failures."""

    def capture_exception(
        self,
        error: BaseException,
        *,
        request_id: str | None = None,
        method: str | None = None,
        route: str | None = None,
    ) -> None:
        raise NotImplementedError


class JsonErrorTracker(ErrorTracker):
    """Default provider: sanitized structured event written to stderr."""

    def __init__(self, stream: TextIO | None = None):
        self.stream = stream

    @staticmethod
    def sanitized_stack(error: BaseException) -> list[str]:
        frames = traceback.extract_tb(error.__traceback__)
        return [
            f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}"
            for frame in frames[-20:]
        ]

    def capture_exception(
        self,
        error: BaseException,
        *,
        request_id: str | None = None,
        method: str | None = None,
        route: str | None = None,
    ) -> None:
        payload = {
            "timestamp": utc_timestamp(),
            "level": "error",
            "event": "unhandled_exception",
            "request_id": request_id,
            "method": method,
            "route": route,
            "error_class": type(error).__name__,
            "stack": self.sanitized_stack(error),
        }
        _write_json(self.stream or sys.stderr, payload)

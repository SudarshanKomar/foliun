import contextvars
import json
import logging
import sys
import time
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response

correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("correlation_id", default=None)


class JsonFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a logging record as JSON."""

        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "correlation_id": getattr(record, "correlation_id", None) or correlation_id_var.get(),
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in {"args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName", "levelname", "levelno", "lineno", "module", "msecs", "message", "msg", "name", "pathname", "process", "processName", "relativeCreated", "stack_info", "thread", "threadName"}:
                continue
            if key in {"api_key", "authorization", "embedding", "content", "file_content"}:
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        encoded = json.dumps(payload, default=str)
        if len(encoded) > 10_240:
            payload["truncated"] = True
            encoded = json.dumps(payload, default=str)[:10_240]
        return encoded


def configure_logging() -> None:
    """Configure application logging."""

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def get_correlation_id() -> str:
    """Return the current correlation ID, creating one if needed."""

    current = correlation_id_var.get()
    if current:
        return current
    generated = str(uuid.uuid4())
    correlation_id_var.set(generated)
    logging.getLogger(__name__).warning("Correlation ID missing; generated a new one")
    return generated


async def correlation_middleware(request: Request, call_next: Callable[[Request], Any]) -> Response:
    """Attach a correlation ID and request log entry to every request."""

    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    token = correlation_id_var.set(correlation_id)
    started = time.perf_counter()
    response: Response | None = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logging.getLogger("foliun.requests").info(
            "API request completed",
            extra={"method": request.method, "path": request.url.path, "status_code": response.status_code if response else 500, "latency_ms": duration_ms, "correlation_id": correlation_id},
        )
        if response:
            response.headers["X-Correlation-ID"] = correlation_id
        correlation_id_var.reset(token)

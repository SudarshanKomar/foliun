import hashlib
import re
from pathlib import Path

from fastapi import UploadFile

from foliun.config import Settings
from foliun.errors import ApiError

SUPPORTED_MIME_TYPES = {"application/pdf", "text/plain"}


def sanitize_filename(filename: str) -> str:
    """Return a filesystem-safe filename."""

    name = Path(filename).name
    sanitized = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip()
    return sanitized or "document"


async def read_and_validate_upload(file: UploadFile, settings: Settings) -> tuple[bytes, str]:
    """Read and validate an uploaded document."""

    if file.content_type not in SUPPORTED_MIME_TYPES:
        raise ApiError(400, "unsupported_file_type", "Only PDF and TXT files are supported")
    content = await file.read()
    if not content:
        raise ApiError(400, "empty_file", "Uploaded file is empty")
    if len(content) > settings.max_upload_bytes:
        raise ApiError(400, "file_too_large", "File size exceeds 50MB limit")
    return content, sanitize_filename(file.filename or "document")


def sha256_bytes(content: bytes) -> str:
    """Return SHA-256 hex digest for bytes."""

    return hashlib.sha256(content).hexdigest()


def store_document_file(content: bytes, filename: str, document_id: str, settings: Settings) -> Path:
    """Store an uploaded file outside web-accessible paths."""

    directory = settings.storage_dir / document_id
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    target.write_bytes(content)
    return target

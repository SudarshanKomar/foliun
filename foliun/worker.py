from uuid import UUID

from arq import Retry
from arq.connections import RedisSettings

from foliun.config import get_settings
from foliun.db import SessionLocal
from foliun.logging_config import configure_logging, correlation_id_var
from foliun.services.ingestion import process_document


async def process_document_job(ctx: dict[str, object], document_id: str, correlation_id: str | None = None) -> None:
    """Process a document ingestion job."""

    if correlation_id:
        correlation_id_var.set(correlation_id)
    job_try = int(ctx.get("job_try", 1))
    backoff_seconds = {1: 1, 2: 4, 3: 16}
    db = SessionLocal()
    try:
        process_document(UUID(document_id), db, mark_failed_on_error=job_try >= 4)
    except Exception as exc:
        if job_try < 4:
            raise Retry(defer=backoff_seconds[job_try]) from exc
        raise
    finally:
        db.close()


class WorkerSettings:
    """arq worker settings."""

    settings = get_settings()
    functions = [process_document_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_tries = 4
    retry_jobs = True
    on_startup = staticmethod(lambda ctx: configure_logging())

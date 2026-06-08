import httpx
from fastapi import APIRouter, Response
from redis import Redis
from sqlalchemy import text

from foliun.config import get_settings
from foliun.db import engine
from foliun.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(response: Response) -> HealthResponse:
    """Return dependency health status."""

    settings = get_settings()
    dependencies: dict[str, str] = {}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        dependencies["postgresql"] = "ok"
    except Exception:
        dependencies["postgresql"] = "unavailable"
    try:
        redis = Redis.from_url(settings.redis_url)
        redis.ping()
        redis.close()
        dependencies["redis"] = "ok"
    except Exception:
        dependencies["redis"] = "unavailable"
    try:
        async with httpx.AsyncClient(timeout=0.5) as client:
            ollama_response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            ollama_response.raise_for_status()
        dependencies["ollama"] = "ok"
    except Exception:
        dependencies["ollama"] = "unavailable"
    if settings.openai_api_key:
        dependencies["openai"] = "configured"
    status = "ok" if all(value in {"ok", "configured"} for value in dependencies.values()) else "degraded"
    if status == "degraded":
        response.status_code = 503
    return HealthResponse(status=status, dependencies=dependencies)

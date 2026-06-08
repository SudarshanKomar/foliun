import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from foliun.config import get_settings
from foliun.db import init_db
from foliun.errors import ApiError, api_error_handler, http_exception_handler, unhandled_exception_handler, validation_exception_handler
from foliun.logging_config import configure_logging, correlation_middleware
from foliun.routers import documents, health, query


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    configure_logging()
    settings = get_settings()
    app = FastAPI(title="Foliun", version="0.1.0")
    app.middleware("http")(correlation_middleware)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_methods=["*"], allow_headers=["*"])
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(query.router, prefix="/api/v1")

    @app.on_event("startup")
    def startup() -> None:
        """Initialize application dependencies."""

        logging.getLogger(__name__).info(
            "Application startup",
            extra={"database_url_configured": bool(settings.database_url), "redis_url_configured": bool(settings.redis_url), "ollama_base_url": settings.ollama_base_url, "embedding_model": settings.embedding_model_name, "reranker_model": settings.reranker_model_name},
        )
        try:
            init_db()
        except Exception:
            logging.getLogger(__name__).exception("Database initialization failed")
        if settings.load_models_at_startup:
            try:
                from foliun.services.embeddings import get_embedder
                from foliun.services.retrieval import get_reranker

                get_embedder()
                get_reranker()
            except Exception:
                logging.getLogger(__name__).critical("Model startup validation failed", exc_info=True)
                raise

    return app


app = create_app()

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(HTTPException):
    """HTTP exception carrying a spec-compliant error code."""

    def __init__(self, status_code: int, error: str, detail: str) -> None:
        """Initialize an API error."""

        super().__init__(status_code=status_code, detail={"error": error, "detail": detail})


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    """Return a spec-compliant API error response."""

    return JSONResponse(status_code=exc.status_code, content=exc.detail)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return validation errors as 400 responses."""

    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(part) for part in first.get("loc", []) if part != "body")
    if first.get("type") == "missing" and field:
        detail = f"Field '{field}' is required"
    elif field == "query":
        detail = "Query must be between 1 and 2000 characters"
    else:
        detail = first.get("msg", "Request validation failed")
    return JSONResponse(status_code=400, content={"error": "validation_error", "detail": detail})


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Return HTTP errors in the standard response shape."""

    if exc.status_code == 404:
        return JSONResponse(status_code=404, content={"error": "not_found", "detail": "Endpoint not found"})
    if isinstance(exc.detail, dict) and {"error", "detail"} <= set(exc.detail):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": "internal_error", "detail": str(exc.detail)})


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return unexpected errors in the standard response shape."""

    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "An unexpected error occurred"})

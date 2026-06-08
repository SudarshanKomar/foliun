from fastapi import Header

from foliun.config import get_settings
from foliun.errors import ApiError


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """Require a valid static API key."""

    if x_api_key is None:
        raise ApiError(401, "unauthorized", "Missing X-API-Key header")
    if x_api_key != get_settings().api_key:
        raise ApiError(401, "unauthorized", "Invalid API key")

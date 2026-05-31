from __future__ import annotations

import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from capture.storage import ASSET_PATH_RE

logger = logging.getLogger("capture.security")

_MCP_METHODS = frozenset({"GET", "POST", "DELETE", "OPTIONS"})
_HEALTHZ_METHODS = frozenset({"GET", "HEAD"})

_PATH_RULES: dict[str, frozenset[str]] = {
    "/healthz": _HEALTHZ_METHODS,
    "/mcp": _MCP_METHODS,
    "/.well-known/oauth-protected-resource": frozenset({"GET", "HEAD", "OPTIONS"}),
}

_ASSET_METHODS = frozenset({"GET", "HEAD"})


def _path_is_allowed(path: str, method: str) -> bool:
    allowed = _PATH_RULES.get(path)
    if allowed is not None:
        return method in allowed
    if method in _ASSET_METHODS and ASSET_PATH_RE.match(path):
        return True
    return False


class AllowlistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()
        if _path_is_allowed(path, method):
            response = await call_next(request)
            _log_allowed(request, response.status_code)
            return response

        client = request.client.host if request.client else "unknown"
        if _log_blocked_probes():
            logger.debug("blocked %s %s from %s", method, path, client)
        return Response(status_code=403, content=b"")


def _log_blocked_probes() -> bool:
    return os.environ.get("CAPTURE_LOG_BLOCKED", "0").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _log_allowed(request: Request, status_code: int) -> None:
    if os.environ.get("CAPTURE_ACCESS_LOG", "1").strip().lower() in {
        "0",
        "false",
        "no",
    }:
        return
    client = request.client.host if request.client else "-"
    logger.info(
        '%s - "%s %s" %s',
        client,
        request.method,
        request.url.path,
        status_code,
    )


def allowed_hosts() -> list[str]:
    raw = os.environ.get(
        "CAPTURE_ALLOWED_HOSTS",
        "localhost,127.0.0.1,capture",
    )
    return [h.strip() for h in raw.split(",") if h.strip()]

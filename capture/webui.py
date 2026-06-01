from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import threading
import time
from collections import deque
from collections.abc import Iterable
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse, Response

logger = logging.getLogger("capture.webui")

_MAX_ENTRIES = 500
_entries: deque[dict] = deque(maxlen=_MAX_ENTRIES)
_lock = threading.Lock()

_STATIC = Path(__file__).resolve().parent / "static"
_SESSION_COOKIE = "capture_webui_session"
_DEFAULT_PIN = "261913"


def enabled() -> bool:
    return os.environ.get("CAPTURE_WEB_UI", "0").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def pin_code() -> str:
    raw = os.environ.get("CAPTURE_WEB_UI_PIN", _DEFAULT_PIN).strip()
    return raw or _DEFAULT_PIN


def _session_token() -> str:
    return hmac.new(
        pin_code().encode(),
        b"capture-webui-session",
        hashlib.sha256,
    ).hexdigest()


def _valid_session(request: Request) -> bool:
    cookie = request.cookies.get(_SESSION_COOKIE)
    if not cookie:
        return False
    expected = _session_token()
    return secrets.compare_digest(cookie, expected)


def _is_webui_path(path: str) -> bool:
    return path == "/webui" or path == "/webui/" or path.startswith("/webui/")


def _is_public_webui(path: str, method: str) -> bool:
    if path == "/webui/login" and method in {"GET", "POST"}:
        return True
    if path == "/webui/login.css" and method == "GET":
        return True
    return False


def links_enabled() -> bool:
    return os.environ.get("CAPTURE_WEB_UI_LINKS", "1").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def record_capture(
    *,
    status: int,
    client: str | None = None,
    source_url: str | None = None,
    image_url: str | None = None,
    error: str | None = None,
) -> None:
    if not enabled():
        return
    entry = {
        "ts": time.time(),
        "status": status,
        "client": client or "-",
        "source_url": source_url,
        "image_url": image_url,
        "error": error,
    }
    with _lock:
        _entries.append(entry)


def _snapshot(limit: int = 200) -> dict:
    with _lock:
        items: Iterable[dict] = list(_entries)
    sliced = list(items)[-limit:]
    return {"total": len(items), "links": links_enabled(), "entries": sliced}


def _static_file(name: str, media_type: str) -> FileResponse:
    response = FileResponse(_STATIC / name, media_type=media_type)
    response.headers["Cache-Control"] = "no-store"
    return response


async def webui_login_page(_request: Request) -> Response:
    if _valid_session(_request):
        return RedirectResponse("/webui", status_code=303)
    return _static_file("login.html", "text/html")


async def webui_login_submit(request: Request) -> Response:
    form = await request.form()
    submitted = form.get("pin", "")
    if not isinstance(submitted, str):
        submitted = ""
    if secrets.compare_digest(submitted, pin_code()):
        response = RedirectResponse("/webui", status_code=303)
        response.set_cookie(
            _SESSION_COOKIE,
            _session_token(),
            httponly=True,
            samesite="lax",
            path="/webui",
        )
        return response
    return RedirectResponse("/webui/login?bad=1", status_code=303)


async def webui_login_css(_request: Request) -> Response:
    return _static_file("login.css", "text/css")


async def webui_dashboard(_request: Request) -> Response:
    return _static_file("webui.html", "text/html")


async def webui_static_css(_request: Request) -> Response:
    return _static_file("webui.css", "text/css")


async def webui_static_js(_request: Request) -> Response:
    return _static_file("webui.js", "application/javascript")


async def webui_api_requests(_request: Request) -> JSONResponse:
    return JSONResponse(_snapshot())


async def webui_api_health(_request: Request) -> JSONResponse:
    with _lock:
        count = len(_entries)
    return JSONResponse({"ok": True, "entries": count})


class WebUIAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()
        if not _is_webui_path(path):
            return await call_next(request)
        if _is_public_webui(path, method):
            return await call_next(request)
        if _valid_session(request):
            return await call_next(request)
        if path.startswith("/webui/api"):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return RedirectResponse("/webui/login", status_code=303)


def webui_routes() -> list:
    from starlette.routing import Route

    return [
        Route("/webui/login", webui_login_page, methods=["GET"]),
        Route("/webui/login", webui_login_submit, methods=["POST"]),
        Route("/webui/login.css", webui_login_css, methods=["GET"]),
        Route("/webui", webui_dashboard, methods=["GET"]),
        Route("/webui/", webui_dashboard, methods=["GET"]),
        Route("/webui/app.css", webui_static_css, methods=["GET"]),
        Route("/webui/app.js", webui_static_js, methods=["GET"]),
        Route("/webui/api/requests", webui_api_requests, methods=["GET"]),
        Route("/webui/api/health", webui_api_health, methods=["GET"]),
    ]


def is_webui_request(request: Request) -> bool:
    return enabled() and _is_webui_path(request.url.path)

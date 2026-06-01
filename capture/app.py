from __future__ import annotations

import contextlib
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.utilities.types import Image
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route

from capture.auth import ApiKeyTokenVerifier, require_api_key
from capture.browser import BrowserPool, browser_pool, capture_page_screenshot
from capture.images import png_to_clean_jpeg
from capture.middleware import AllowlistMiddleware, allowed_hosts
from capture.routes import serve_asset
from capture.storage import ensure_asset_dir, public_url, store_jpeg
from capture.validate import UrlValidationError, validate_capture_url
from capture.webui import WebUIAuthMiddleware, enabled as webui_enabled
from capture.webui import record_capture as webui_record_capture
from capture.webui import webui_routes

logging.basicConfig(
    level=os.environ.get("CAPTURE_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("capture")

CAPTURE_BASE_URL = os.environ.get(
    "CAPTURE_BASE_URL", "http://localhost:8000"
).rstrip("/")

_SERVER_INSTRUCTIONS = (
    "Capture screenshots public web pages and returns a JPEG inline plus image_url. "
    "Use capture_screenshot with a full http or https URL. Structured output includes "
    "image_url for embedding. Only public URLs are allowed."
)


@dataclass
class AppContext:
    pool: BrowserPool


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncIterator[AppContext]:
    async with browser_pool() as pool:
        logger.info("Chromium browser started")
        yield AppContext(pool=pool)
        logger.info("Chromium browser stopped")


mcp = FastMCP(
    "Capture",
    instructions=_SERVER_INSTRUCTIONS,
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
    port=int(os.environ.get("CAPTURE_PORT", "8000")),
    token_verifier=ApiKeyTokenVerifier(require_api_key()),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(CAPTURE_BASE_URL),
        resource_server_url=AnyHttpUrl(CAPTURE_BASE_URL),
        required_scopes=[],
    ),
    lifespan=app_lifespan,
)

_CAPTURE_ANNOTATIONS = ToolAnnotations(
    title="Capture webpage screenshot",
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=True,
    idempotentHint=True,
)


def _tool_client(ctx: Context) -> str | None:
    req = getattr(ctx.request_context, "request", None)
    if req is None or req.client is None:
        return None
    return req.client.host


@mcp.tool(
    name="capture_screenshot",
    title="Capture webpage screenshot",
    description=(
        "Capture a JPEG screenshot of a public web page. Returns the image inline "
        "and an embeddable image_url (no auth on the hosted copy). Uses a headless "
        "browser, strips metadata, and stores the file at an unguessable URL."
    ),
    annotations=_CAPTURE_ANNOTATIONS,
    structured_output=True,
)
async def capture_screenshot(url: str, ctx: Context) -> CallToolResult:
    client = _tool_client(ctx)
    try:
        target = validate_capture_url(url)
    except UrlValidationError as exc:
        rejected = url.strip() if isinstance(url, str) else None
        error = str(exc)
        if rejected:
            error = f"{error}: {rejected[:500]}"
        webui_record_capture(
            status=400,
            client=client,
            source_url=None,
            error=error,
        )
        raise ValueError(str(exc)) from exc

    app_ctx: AppContext = ctx.request_context.lifespan_context
    try:
        png = await capture_page_screenshot(app_ctx.pool, target)
        jpeg = png_to_clean_jpeg(png)
        asset_path = store_jpeg(jpeg)
        image_url = public_url(asset_path)
    except Exception as exc:
        webui_record_capture(
            status=500,
            client=client,
            source_url=target,
            error=str(exc),
        )
        raise

    webui_record_capture(
        status=200,
        client=client,
        source_url=target,
        image_url=image_url,
    )

    structured: dict[str, Any] = {
        "image_url": image_url,
        "source_url": target,
        "format": "image/jpeg",
        "width_hint": "embed using markdown ![screenshot](image_url) or HTML <img>",
    }

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=(
                    f"Screenshot of {target}. Hosted at {image_url} "
                    "(no API key required to view)."
                ),
            ),
            Image(data=jpeg, format="jpeg").to_image_content(),
        ],
        structuredContent=structured,
    )


async def healthz(_request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


@contextlib.asynccontextmanager
async def starlette_lifespan(_app: Starlette) -> AsyncIterator[None]:
    ensure_asset_dir()
    async with mcp.session_manager.run():
        yield


_routes = [
    Route("/healthz", healthz, methods=["GET", "HEAD"]),
    Route("/r/{token}.jpg", serve_asset, methods=["GET", "HEAD"]),
]
if webui_enabled():
    _routes.extend(webui_routes())
_routes.append(Mount("/", mcp.streamable_http_app()))

app = Starlette(
    routes=_routes,
    lifespan=starlette_lifespan,
)

app.add_middleware(AllowlistMiddleware)
if webui_enabled():
    app.add_middleware(WebUIAuthMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())

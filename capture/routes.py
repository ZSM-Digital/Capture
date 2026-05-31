from __future__ import annotations

from starlette.requests import Request
from starlette.responses import FileResponse, Response

from capture.storage import resolve_asset_path

_CACHE = "public, max-age=604800, immutable"


async def serve_asset(request: Request) -> Response:
    path = resolve_asset_path(request.url.path)
    if path is None:
        return Response(status_code=404, content=b"")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={
            "Cache-Control": _CACHE,
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )

from __future__ import annotations

import logging
import os
import re
import secrets
import time
from pathlib import Path

logger = logging.getLogger("capture.storage")

ASSET_DIR = Path(os.environ.get("CAPTURE_ASSET_DIR", "/var/lib/capture/assets"))
ASSET_TTL_SECONDS = int(os.environ.get("CAPTURE_ASSET_TTL_HOURS", "168")) * 3600
PUBLIC_PREFIX = os.environ.get("CAPTURE_ASSET_PATH_PREFIX", "/r").rstrip("/")
PUBLIC_BASE_URL = os.environ.get(
    "CAPTURE_PUBLIC_BASE_URL",
    os.environ.get("CAPTURE_BASE_URL", "http://localhost:8000"),
).rstrip("/")

TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{43,86}$")
ASSET_PATH_RE = re.compile(
    rf"^{re.escape(PUBLIC_PREFIX)}/([A-Za-z0-9_-]{{43,86}})\.jpg$"
)


def ensure_asset_dir() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)


def store_jpeg(jpeg_bytes: bytes) -> str:
    ensure_asset_dir()
    purge_expired_assets()
    token = secrets.token_urlsafe(48)
    path = ASSET_DIR / f"{token}.jpg"
    path.write_bytes(jpeg_bytes)
    return f"{PUBLIC_PREFIX}/{token}.jpg"


def public_url(asset_path: str) -> str:
    return f"{PUBLIC_BASE_URL}{asset_path}"


def resolve_asset_path(url_path: str) -> Path | None:
    match = ASSET_PATH_RE.match(url_path)
    if not match:
        return None
    token = match.group(1)
    if not TOKEN_RE.fullmatch(token):
        return None
    candidate = (ASSET_DIR / f"{token}.jpg").resolve()
    try:
        candidate.relative_to(ASSET_DIR.resolve())
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


def purge_expired_assets() -> None:
    if ASSET_TTL_SECONDS <= 0:
        return
    if not ASSET_DIR.exists():
        return
    cutoff = time.time() - ASSET_TTL_SECONDS
    removed = 0
    for entry in ASSET_DIR.glob("*.jpg"):
        try:
            if entry.stat().st_mtime < cutoff:
                entry.unlink(missing_ok=True)
                removed += 1
        except OSError:
            logger.debug("failed to purge %s", entry, exc_info=True)
    if removed:
        logger.debug("purged %s expired assets", removed)

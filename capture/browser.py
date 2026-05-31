from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Literal

from playwright.async_api import Browser, Playwright, async_playwright

from capture.images import trim_png_to_width

logger = logging.getLogger(__name__)

PrepareMode = Literal["strict", "lenient", "minimal", "none"]

_SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"

DEFAULT_TIMEOUT_MS = int(os.environ.get("CAPTURE_TIMEOUT_MS", "30000"))
DEFAULT_VIEWPORT_WIDTH = int(os.environ.get("CAPTURE_VIEWPORT_WIDTH", "1280"))
DEFAULT_VIEWPORT_HEIGHT = int(os.environ.get("CAPTURE_VIEWPORT_HEIGHT", "720"))
SCROLL_STEP_DELAY_MS = int(os.environ.get("CAPTURE_SCROLL_STEP_DELAY_MS", "150"))
SCROLL_END_PAUSE_MS = int(os.environ.get("CAPTURE_SCROLL_END_PAUSE_MS", "400"))
SCROLL_TOP_PAUSE_MS = int(os.environ.get("CAPTURE_SCROLL_TOP_PAUSE_MS", "300"))
SCROLL_TOP_VERIFY_MS = int(os.environ.get("CAPTURE_SCROLL_TOP_VERIFY_MS", "75"))
SCROLL_TOP_MAX_ATTEMPTS = int(os.environ.get("CAPTURE_SCROLL_TOP_MAX_ATTEMPTS", "12"))
MAX_SCROLL_STEPS = int(os.environ.get("CAPTURE_MAX_SCROLL_STEPS", "80"))
CAPTURE_MAX_ATTEMPTS = int(os.environ.get("CAPTURE_MAX_ATTEMPTS", "4"))


def _script(name: str) -> str:
    return (_SCRIPTS_DIR / name).read_text(encoding="utf-8")


def _substitute(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace(f"__{key}__", value)
    return out


def _scroll_page_js() -> str:
    return _substitute(
        _script("scroll_page.js"),
        {
            "STEP_DELAY": str(SCROLL_STEP_DELAY_MS),
            "END_PAUSE": str(SCROLL_END_PAUSE_MS),
            "MAX_STEPS": str(MAX_SCROLL_STEPS),
        },
    )


def _prepare_fullpage_screenshot_js(*, strict: bool = True) -> str:
    width_fail_name = (
        "prepare_width_fail_strict.js" if strict else "prepare_width_fail_lenient.js"
    )
    return _substitute(
        _script("prepare_fullpage.js"),
        {
            "TOP_PAUSE": str(SCROLL_TOP_PAUSE_MS),
            "VERIFY_DELAY": str(SCROLL_TOP_VERIFY_MS),
            "MAX_ATTEMPTS": str(SCROLL_TOP_MAX_ATTEMPTS),
            "WIDTH_FAIL": _script(width_fail_name).strip(),
        },
    )


def _prepare_minimal_screenshot_js() -> str:
    return _script("prepare_minimal.js")


@dataclass
class BrowserPool:
    playwright: Playwright
    browser: Browser


@asynccontextmanager
async def browser_pool() -> AsyncIterator[BrowserPool]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            yield BrowserPool(playwright=playwright, browser=browser)
        finally:
            await browser.close()


async def _scroll_page_to_load_lazy_content(page) -> None:
    logger.debug("scrolling page to trigger lazy-loaded content")
    await page.evaluate(_scroll_page_js())


async def _prepare_fullpage_screenshot(page, *, strict: bool = True) -> None:
    logger.debug("preparing page for full-page screenshot (strict=%s)", strict)
    await page.evaluate(_prepare_fullpage_screenshot_js(strict=strict))


async def _prepare_minimal_screenshot(page) -> None:
    logger.debug("minimal page prep for screenshot")
    await page.evaluate(_prepare_minimal_screenshot_js())


async def _load_page(page, url: str) -> None:
    try:
        await page.goto(
            url,
            wait_until="networkidle",
            timeout=DEFAULT_TIMEOUT_MS,
        )
    except Exception:
        logger.info("networkidle timed out for %s, falling back to load", url)
        await page.goto(
            url,
            wait_until="load",
            timeout=DEFAULT_TIMEOUT_MS,
        )


async def _capture_page_once(
    pool: BrowserPool,
    url: str,
    *,
    prepare: PrepareMode,
    scroll_lazy: bool,
) -> bytes:
    page = await pool.browser.new_page(
        viewport={
            "width": DEFAULT_VIEWPORT_WIDTH,
            "height": DEFAULT_VIEWPORT_HEIGHT,
        }
    )
    try:
        await _load_page(page, url)
        if scroll_lazy:
            await _scroll_page_to_load_lazy_content(page)
        if prepare == "strict":
            await _prepare_fullpage_screenshot(page, strict=True)
        elif prepare == "lenient":
            await _prepare_fullpage_screenshot(page, strict=False)
        elif prepare == "minimal":
            await _prepare_minimal_screenshot(page)
        png = await page.screenshot(type="png", full_page=True)
        return trim_png_to_width(png, DEFAULT_VIEWPORT_WIDTH)
    finally:
        await page.close()


async def capture_page_screenshot(pool: BrowserPool, url: str) -> bytes:
    attempts: list[tuple[str, PrepareMode, bool]] = [
        ("strict", "strict", True),
        ("lenient", "lenient", True),
        ("minimal", "minimal", True),
        ("bare", "none", False),
    ]
    attempts = attempts[: max(1, CAPTURE_MAX_ATTEMPTS)]

    last_error: Exception | None = None
    for index, (name, prepare, scroll_lazy) in enumerate(attempts, start=1):
        try:
            png = await _capture_page_once(
                pool,
                url,
                prepare=prepare,
                scroll_lazy=scroll_lazy,
            )
            if index > 1:
                logger.info(
                    "capture succeeded for %s on attempt %s (%s)",
                    url,
                    index,
                    name,
                )
            return png
        except Exception as exc:
            last_error = exc
            logger.warning(
                "capture attempt %s/%s (%s) failed for %s: %s",
                index,
                len(attempts),
                name,
                url,
                exc,
            )

    assert last_error is not None
    raise last_error

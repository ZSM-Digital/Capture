from __future__ import annotations

import io
import os

from PIL import Image

DEFAULT_JPEG_QUALITY = int(os.environ.get("CAPTURE_JPEG_QUALITY", "82"))


def trim_png_to_width(png_bytes: bytes, target_width: int) -> bytes:
    if target_width <= 0:
        return png_bytes
    with Image.open(io.BytesIO(png_bytes)) as img:
        if img.width <= target_width:
            return png_bytes
        cropped = img.crop((0, 0, target_width, img.height))
        buf = io.BytesIO()
        cropped.save(buf, format="PNG", optimize=True)
        return buf.getvalue()


def png_to_clean_jpeg(png_bytes: bytes, *, quality: int | None = None) -> bytes:
    q = quality if quality is not None else DEFAULT_JPEG_QUALITY
    with Image.open(io.BytesIO(png_bytes)) as img:
        rgb = img.convert("RGB")
        buf = io.BytesIO()
        rgb.save(
            buf,
            format="JPEG",
            quality=q,
            optimize=True,
            progressive=True,
            subsampling="4:2:0",
        )
    return buf.getvalue()

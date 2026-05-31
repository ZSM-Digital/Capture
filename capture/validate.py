from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_ALLOWED_SCHEMES = frozenset({"http", "https"})


class UrlValidationError(ValueError):
    pass


def validate_capture_url(url: str) -> str:
    if url is None or not isinstance(url, str):
        raise UrlValidationError("url is required")

    raw = url.strip()
    if not raw:
        raise UrlValidationError("url is required")

    parsed = urlparse(raw)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UrlValidationError("url must use http or https")

    if not parsed.netloc:
        raise UrlValidationError("url must include a host")

    if parsed.username or parsed.password:
        raise UrlValidationError("url must not include credentials")

    host = parsed.hostname
    if not host:
        raise UrlValidationError("url must include a valid host")

    _reject_private_host(host)
    return raw


def _reject_private_host(host: str) -> None:
    lowered = host.lower().rstrip(".")
    if lowered in {"localhost", "localhost.localdomain"}:
        raise UrlValidationError("url host is not allowed")

    try:
        addr = ipaddress.ip_address(lowered)
    except ValueError:
        try:
            infos = socket.getaddrinfo(lowered, None, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise UrlValidationError(f"url host could not be resolved: {host}") from exc
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise UrlValidationError("url host is not allowed")
        return

    if (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    ):
        raise UrlValidationError("url host is not allowed")

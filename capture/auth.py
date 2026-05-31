from __future__ import annotations

import os
import secrets

from mcp.server.auth.provider import AccessToken, TokenVerifier


def require_api_key() -> str:
    key = os.environ.get("CAPTURE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing required environment variable: CAPTURE_API_KEY")
    return key


class ApiKeyTokenVerifier(TokenVerifier):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or not secrets.compare_digest(token, self._api_key):
            return None
        return AccessToken(
            token=token,
            client_id="capture-client",
            scopes=[],
        )

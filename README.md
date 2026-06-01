# Capture

MCP server that captures full-page JPEG screenshots of public web pages. Self-host with Docker or run locally.

## Quick start

1. Clone this repository.
2. Copy the example environment file: `cp .env.example .env`
3. Generate an API key and set `CAPTURE_API_KEY` in `.env`:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
4. Build and start: `docker compose up -d --build`
5. Wait for the health check (Chromium needs ~45s on first boot).
6. Verify: `curl http://localhost:8000/healthz` → `ok`
7. Point your MCP client at `http://localhost:8000/mcp` with Bearer auth (see below).

## Tool

| Name | Input | Output |
|------|-------|--------|
| `capture_screenshot` | `url` (http/https) | Inline JPEG + structured `image_url`, `source_url`, `format` |

Screenshots are re-encoded as JPEG with metadata stripped, stored under unguessable paths like `http://localhost:8000/r/<token>.jpg`. The image URL is public (no API key). The MCP endpoint `/mcp` requires Bearer authentication.

Non-public URLs (localhost, private IPs, etc.) are rejected.

## Project layout

```
.
├── capture/              Application package
│   ├── app.py            Starlette app, MCP tool, routes
│   ├── auth.py           Bearer token verification
│   ├── browser.py        Playwright capture logic
│   ├── images.py         JPEG encoding
│   ├── middleware.py     Path and access logging
│   ├── routes.py         Public asset handler
│   ├── storage.py        Asset storage and URLs
│   ├── validate.py       URL validation (SSRF guards)
│   └── scripts/          Page-prep scripts for Playwright
├── docs/
│   └── CHATGPT.md        ChatGPT connector guide
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

Run locally (from the repo root, with dependencies installed):

```bash
python -m capture
```

## Client configuration

Send the API key on every MCP request:

```
Authorization: Bearer <CAPTURE_API_KEY>
```

Example Cursor `mcp.json`:

```json
{
  "mcpServers": {
    "capture": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

Use HTTPS in production.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAPTURE_API_KEY` | *(required)* | Bearer token for `/mcp` |
| `CAPTURE_BASE_URL` | `http://localhost:8000` | Issuer URL for MCP auth metadata |
| `CAPTURE_PUBLIC_BASE_URL` | same as `CAPTURE_BASE_URL` | Base URL for `image_url` links |
| `CAPTURE_ALLOWED_HOSTS` | `localhost,127.0.0.1,capture` | Comma-separated `Host` header allowlist |
| `CAPTURE_PORT` | `8000` | Listen port (non-Docker runs) |
| `CAPTURE_LOG_LEVEL` | `INFO` | Python log level |
| `CAPTURE_JPEG_QUALITY` | `82` | JPEG quality (1–95) |
| `CAPTURE_ASSET_TTL_HOURS` | `168` | Hours before purging stored JPEGs |
| `CAPTURE_ASSET_DIR` | `/var/lib/capture/assets` | On-disk asset directory |
| `CAPTURE_ACCESS_LOG` | `1` | Log allowed requests (`0` to disable) |
| `CAPTURE_LOG_BLOCKED` | `0` | Log blocked probes (`1` to enable) |
| `CAPTURE_TIMEOUT_MS` | `30000` | Page load timeout |
| `CAPTURE_VIEWPORT_WIDTH` | `1280` | Browser viewport width |
| `CAPTURE_VIEWPORT_HEIGHT` | `720` | Browser viewport height |
| `CAPTURE_WEB_UI` | `0` | Enable capture log dashboard at `/webui` |
| `CAPTURE_WEB_UI_PIN` | `261913` | PIN required to access the web UI |
| `CAPTURE_WEB_UI_LINKS` | `1` | Clickable source and screenshot URLs in the web UI (`0` for plain text) |

See `.env.example` for a minimal working set.

## Security

- **SSRF protection:** URL validation blocks localhost, private/reserved IPs, and credentials in URLs.
- **Path allowlist:** Only `/healthz`, `/mcp`, OAuth discovery, and `/r/<token>.jpg` are served; everything else returns **403**.
- **Host allowlist:** Unexpected `Host` headers are rejected.
- **Public assets:** JPEG tokens are long and unguessable; no directory listing.

## Production

1. Set `CAPTURE_BASE_URL` and `CAPTURE_PUBLIC_BASE_URL` to your public HTTPS origin.
2. Add your public hostname to `CAPTURE_ALLOWED_HOSTS`.
3. Put the service behind a reverse proxy (nginx, Caddy, Traefik, etc.) with TLS. Enable WebSocket support if your client uses streaming.
4. Use a strong `CAPTURE_API_KEY` and keep `.env` out of version control.

## ChatGPT

See **[docs/CHATGPT.md](docs/CHATGPT.md)** for connecting via ChatGPT Developer Mode.

## Health and logs

```bash
curl http://localhost:8000/healthz
docker logs -f capture
```

## Licence

MIT — see [LICENSE](LICENSE).

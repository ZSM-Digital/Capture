# Connecting Capture to ChatGPT

ChatGPT exposes MCP tools as **actions**. If you see *"doesn't have any actions yet"*, the server is usually fine — connector setup or per-chat enablement is incomplete.

## Requirements

1. **Developer mode** — Settings → Apps & Connectors → Advanced → enable **Developer mode** (Pro, Team, Enterprise, or Edu). Screenshot-only servers are action apps, not search/fetch connectors.

2. **Connector URL** — must end with `/mcp`, e.g. `https://your-host.example/mcp` (local testing: `http://localhost:8000/mcp` only works if ChatGPT can reach your machine).

3. **Authentication** — Configure a **Bearer token** matching `CAPTURE_API_KEY` from your `.env`:
   ```
   Authorization: Bearer YOUR_KEY
   ```

4. **Enable per chat** — New chat → **+** → **More** → **Developer mode** → turn on **Capture**.

5. **Refresh after deploy** — Settings → Connectors → your connector → **Refresh** to reload tool metadata.

## Verify tools are advertised

From the host (replace the URL if not local):

```bash
docker exec capture python -c "
import asyncio, os
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
async def main():
    h = {'Authorization': 'Bearer ' + os.environ['CAPTURE_API_KEY']}
    async with streamablehttp_client('http://127.0.0.1:8000/mcp', headers=h) as p:
        async with ClientSession(p[0], p[1]) as s:
            await s.initialize()
            for t in (await s.list_tools()).tools:
                print(t.name, t.title, t.annotations)
asyncio.run(main())
"
```

You should see `capture_screenshot` with `readOnlyHint=True`.

## Using it in chat

Example prompts:

- *"Screenshot https://example.com and describe the layout"*
- *"Use capture_screenshot on https://example.com"*

The tool returns the JPEG inline plus `image_url` in structured output for markdown embeds.

## Deep Research / Company knowledge

Those modes expect `search` and `fetch` tools. Capture is an action app (screenshots). Use normal **Chat** with Developer Mode enabled.

## Troubleshooting

| Symptom | Fix |
|--------|-----|
| No actions yet | Enable Developer mode; refresh connector; enable connector in the chat |
| 401 on `/mcp` | Set Bearer token in connector auth |
| Works in Cursor, not ChatGPT | URL must end with `/mcp`; connector enabled in that chat |

References: [Connect from ChatGPT](https://developers.openai.com/apps-sdk/deploy/connect-chatgpt), [Build your MCP server](https://developers.openai.com/apps-sdk/build/mcp-server).

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "capture.app:app",
        host="0.0.0.0",
        port=int(os.environ.get("CAPTURE_PORT", "8000")),
        log_level=os.environ.get("CAPTURE_LOG_LEVEL", "info").lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()

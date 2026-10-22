"""Single-worker container launcher. Forwarding headers never select an origin."""

import os

import uvicorn


def main() -> None:
    port = os.environ.get("PORT", "8000")
    if not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise SystemExit("PORT must be an integer from 1 to 65535")
    uvicorn.run(
        "forge_api.main:app",
        host="0.0.0.0",
        port=int(port),
        workers=1,
        proxy_headers=False,
        access_log=False,
        server_header=False,
    )


if __name__ == "__main__":
    main()

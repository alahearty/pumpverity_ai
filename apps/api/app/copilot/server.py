import hmac
import logging

import uvicorn
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from app.copilot.tools import mcp_server
from app.core.config import get_settings

logger = logging.getLogger("pumpverity.copilot.mcp.http")


def create_http_app():
    inner = mcp_server.streamable_http_app()
    expected = f"Bearer {get_settings().mcp_service_token_value}".encode()

    async def app(scope, receive, send):
        if scope["type"] == "http":
            headers = Headers(scope=scope)
            provided = headers.get("authorization", "").encode()
            if not provided or not hmac.compare_digest(provided, expected):
                response = JSONResponse(
                    {"error": "MCP service authentication required."},
                    status_code=401,
                )
                await response(scope, receive, send)
                return
        await inner(scope, receive, send)

    return app


def main() -> None:
    settings = get_settings()
    logger.info(
        "mcp_server_starting",
        extra={"host": settings.mcp_host, "port": settings.mcp_port},
    )
    uvicorn.run(
        create_http_app(),
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

import anyio
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.memory import create_client_server_memory_streams
from mcp.types import Tool

from app.copilot.tools import mcp_server
from app.core.config import get_settings

logger = logging.getLogger("pumpverity.copilot.mcp.client")
MAX_RESULT_BYTES = 512_000


class McpToolError(RuntimeError):
    def __init__(self, message: str, *, code: str = "MCP_TOOL_ERROR") -> None:
        super().__init__(message)
        self.code = code


class McpUnavailableError(RuntimeError):
    pass


def _result_payload(result) -> dict[str, Any]:
    if result.isError:
        text = " ".join(
            item.text for item in result.content if getattr(item, "type", None) == "text"
        )
        raise McpToolError(text or "MCP tool returned an error.")
    if result.structuredContent is not None:
        payload = result.structuredContent
    else:
        texts = [item.text for item in result.content if getattr(item, "type", None) == "text"]
        if not texts:
            raise McpToolError("MCP tool returned no structured result.", code="MCP_EMPTY_RESULT")
        try:
            payload = json.loads(texts[0])
        except json.JSONDecodeError as exc:
            raise McpToolError(
                "MCP tool returned a non-JSON result.", code="MCP_INVALID_RESULT"
            ) from exc
    if not isinstance(payload, dict):
        raise McpToolError("MCP tool result must be an object.", code="MCP_INVALID_RESULT")
    if len(json.dumps(payload, default=str).encode("utf-8")) > MAX_RESULT_BYTES:
        raise McpToolError("MCP tool result exceeded the size limit.", code="MCP_RESULT_TOO_LARGE")
    return payload


class McpSession:
    def __init__(self, session: ClientSession, timeout_seconds: float) -> None:
        self._session = session
        self._timeout = timeout_seconds

    async def list_tools(self) -> list[Tool]:
        async with asyncio.timeout(self._timeout):
            result = await self._session.list_tools()
        return list(result.tools)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            async with asyncio.timeout(self._timeout):
                result = await self._session.call_tool(
                    name,
                    arguments,
                    read_timeout_seconds=timedelta(seconds=self._timeout),
                )
            return _result_payload(result)
        except TimeoutError as exc:
            raise McpToolError(f"MCP tool {name} timed out.", code="MCP_TOOL_TIMEOUT") from exc
        except McpToolError:
            raise
        except Exception as exc:
            raise McpToolError(f"MCP tool {name} failed: {exc}", code="MCP_TOOL_FAILED") from exc


async def _run_memory_server(server_streams) -> None:
    try:
        await mcp_server._mcp_server.run(
            server_streams[0],
            server_streams[1],
            mcp_server._mcp_server.create_initialization_options(),
        )
    except (anyio.ClosedResourceError, anyio.BrokenResourceError):
        return


class McpClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @asynccontextmanager
    async def connect(self):
        if not self.settings.copilot_enabled:
            raise McpUnavailableError("The Engineering Copilot is disabled.")
        timeout = self.settings.mcp_tool_timeout_seconds
        try:
            if self.settings.mcp_transport == "http":
                headers = {
                    "Authorization": f"Bearer {self.settings.mcp_service_token_value}",
                    "User-Agent": "pumpverity-copilot/0.6",
                }
                async with (
                    httpx.AsyncClient(headers=headers, timeout=timeout) as http_client,
                    streamable_http_client(
                        self.settings.mcp_server_url, http_client=http_client
                    ) as (read_stream, write_stream, _session_id),
                    ClientSession(
                        read_stream,
                        write_stream,
                        read_timeout_seconds=timedelta(seconds=timeout),
                    ) as session,
                ):
                    await session.initialize()
                    yield McpSession(session, timeout)
                return
            async with (
                create_client_server_memory_streams() as (
                    client_streams,
                    server_streams,
                ),
                anyio.create_task_group() as task_group,
            ):
                task_group.start_soon(_run_memory_server, server_streams)
                async with ClientSession(
                    client_streams[0],
                    client_streams[1],
                    read_timeout_seconds=timedelta(seconds=timeout),
                ) as session:
                    await session.initialize()
                    yield McpSession(session, timeout)
                task_group.cancel_scope.cancel()
        except McpUnavailableError:
            raise
        except Exception as exc:
            logger.warning("mcp_connection_failed", extra={"error": str(exc)})
            raise McpUnavailableError(f"The MCP server is unavailable: {exc}") from exc


def get_mcp_client() -> McpClient:
    return McpClient()

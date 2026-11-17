import asyncio

import pytest
from app.copilot.client import McpClient, McpSession, McpToolError
from app.copilot.server import create_http_app
from app.core.config import get_settings
from app.db.models import User
from fastapi.testclient import TestClient
from sqlalchemy import select
from tests.test_predictions import _setup_equipment_and_window

READ_TOOLS = {
    "pumpverity_get_monitoring_overview",
    "pumpverity_get_pump_status",
    "pumpverity_get_sensor_health",
    "pumpverity_get_latest_prediction",
    "pumpverity_get_fault_history",
    "pumpverity_get_vibration_summary",
    "pumpverity_get_model_evaluation",
    "pumpverity_get_alert_details",
    "pumpverity_get_edge_connectivity",
}
WRITE_TOOLS = {
    "pumpverity_acknowledge_alert",
    "pumpverity_mark_alert_reviewed",
    "pumpverity_add_engineering_note",
    "pumpverity_generate_monitoring_report",
}


def _run(coro):
    return asyncio.run(coro)


def test_mcp_tool_discovery_has_strict_contracts(client):
    async def discover():
        async with McpClient().connect() as session:
            return await session.list_tools()

    tools = _run(discover())
    names = {tool.name for tool in tools}
    assert names == READ_TOOLS | WRITE_TOOLS
    for tool in tools:
        assert tool.description
        assert tool.inputSchema["type"] == "object"
        assert tool.outputSchema is not None
        assert tool.outputSchema.get("type") == "object"


def test_mcp_read_tool_invokes_domain_services_with_provenance(client, db):
    engineer, pump, sensor, _session, _window = _setup_equipment_and_window(client)
    actor = db.execute(
        select(User).where(User.email == "engineer@petrosense.local")
    ).scalar_one()

    async def read_status():
        async with McpClient().connect() as session:
            return await session.call_tool(
                "pumpverity_get_pump_status",
                {"actor_id": actor.id, "pump_id": pump["id"]},
            )

    result = _run(read_status())
    assert result["pump_id"] == pump["id"]
    assert result["pump_code"] == "PRED-PUMP-01"
    assert result["data_mode"] == "SIMULATED_REPLAY"
    assert result["sensors"][0]["latest_rms_g"] == pytest.approx(0.035)
    assert "simulated" in result["notice"].lower()
    assert actor.id

    async def read_sensor():
        async with McpClient().connect() as session:
            return await session.call_tool(
                "pumpverity_get_sensor_health",
                {
                    "actor_id": actor.id,
                    "pump_id": pump["id"],
                    "sensor_id": sensor["id"],
                },
            )

    health = _run(read_sensor())
    assert health["sensors"][0]["sensor_code"] == "PRED-VIB-01"
    assert health["sensors"][0]["sampling_status"] in {"RECENT", "STALE"}
    assert health["sensors"][0]["latest_rms_g"] == pytest.approx(0.035)
    assert "simulated" in health["notice"].lower()
    assert engineer


def test_mcp_invalid_actor_and_equipment_are_structured_errors(client, db):
    _engineer, _pump, _sensor, _session, _window = _setup_equipment_and_window(client)
    actor = db.execute(
        select(User).where(User.email == "engineer@petrosense.local")
    ).scalar_one()

    async def bad_actor():
        async with McpClient().connect() as session:
            with pytest.raises(
                McpToolError, match=r"UNAUTHENTICATED|not an active user"
            ):
                await session.call_tool(
                    "pumpverity_get_monitoring_overview",
                    {"actor_id": "00000000-0000-0000-0000-000000000000"},
                )

    _run(bad_actor())

    async def bad_pump():
        async with McpClient().connect() as session:
            with pytest.raises(McpToolError, match="PUMP_NOT_FOUND"):
                await session.call_tool(
                    "pumpverity_get_pump_status",
                    {
                        "actor_id": actor.id,
                        "pump_id": "00000000-0000-0000-0000-000000000000",
                    },
                )

    _run(bad_pump())


def test_mcp_client_timeout_is_reported_as_tool_error():
    class SlowSession:
        async def call_tool(self, *_args, **_kwargs):
            await asyncio.sleep(0.05)

    async def slow_call():
        session = McpSession(SlowSession(), timeout_seconds=0.001)
        with pytest.raises(McpToolError, match="timed out"):
            await session.call_tool("pumpverity_get_pump_status", {})

    _run(slow_call())


def test_http_mcp_requires_service_token():
    with TestClient(create_http_app()) as http_client:
        unauthenticated = http_client.post("/mcp", json={})
        assert unauthenticated.status_code == 401
        authenticated = http_client.post(
            "/mcp",
            json={},
            headers={
                "Authorization": f"Bearer {get_settings().mcp_service_token_value}"
            },
        )
        assert authenticated.status_code != 401

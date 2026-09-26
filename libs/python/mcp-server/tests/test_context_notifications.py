"""Progress and log notifications from the cua tools must reach the MCP client."""

import pytest
from mcp.shared.memory import create_connected_server_and_client_session


@pytest.mark.asyncio
async def test_run_multi_cua_tasks_progress_reaches_client():
    from mcp_server.server import serve

    progress = []

    async def on_progress(value, total, message):
        progress.append(value)

    async with create_connected_server_and_client_session(serve()._mcp_server) as client:
        result = await client.call_tool(
            "run_multi_cua_tasks", {"tasks": []}, progress_callback=on_progress
        )

    assert not result.isError
    assert progress == [1.0]

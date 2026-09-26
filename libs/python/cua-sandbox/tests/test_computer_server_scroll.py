"""Mouse.scroll over the computer-server transports must scroll at (x, y) by (scroll_x, scroll_y).

computer-server's ``scroll`` handler is ``scroll(x, y)`` where x and y are the
scroll amounts, and it drops any parameter the handler does not declare
(``computer_server/main.py`` filters params by the handler signature). The fake
server below applies the same rule to the real handler signatures.
"""

from __future__ import annotations

import inspect
import json

import httpx
import pytest
from cua_sandbox.interfaces.mouse import Mouse
from cua_sandbox.transport.fleet import FleetTransport
from cua_sandbox.transport.http import HTTPTransport
from fleet_sdk import HttpResponse, Sandbox

pytestmark = pytest.mark.asyncio


class FakeComputerServer:
    """Dispatches /cmd bodies the way computer-server does."""

    def __init__(self):
        self.calls = []

    def move_cursor(self, x: int, y: int):
        self.calls.append(("move_cursor", x, y))

    def scroll(self, x: int, y: int):
        self.calls.append(("scroll", x, y))

    def handle(self, body: bytes) -> str:
        data = json.loads(body)
        handler = getattr(self, data["command"])
        params = data.get("params", {})
        accepted = inspect.signature(handler).parameters
        handler(**{k: v for k, v in params.items() if k in accepted})
        return 'data: {"success": true}\n\n'


async def test_http_transport_scrolls_at_position_by_amount():
    server = FakeComputerServer()
    transport = HTTPTransport("http://server:8000")
    transport._client = httpx.AsyncClient(
        base_url="http://server:8000",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=server.handle(request.content))
        ),
    )

    await Mouse(transport).scroll(640, 360, scroll_x=0, scroll_y=-3)

    assert server.calls == [("move_cursor", 640, 360), ("scroll", 0, -3)]


async def test_fleet_transport_scrolls_at_position_by_amount():
    server = FakeComputerServer()

    class SDK:
        async def service_request(self, sandbox, service, path, request):
            return HttpResponse(status=200, headers=[], body=server.handle(request.body).encode())

    transport = FleetTransport(
        sdk=SDK(),
        bound=Sandbox(namespace="demo", claim="c", name="sb", services=["api"]),
    )
    await transport.connect()

    await Mouse(transport).scroll(640, 360, scroll_x=0, scroll_y=-3)

    assert server.calls == [("move_cursor", 640, 360), ("scroll", 0, -3)]


async def test_raw_server_form_scroll_passes_through():
    from cua_sandbox.transport.computer_server import scroll_commands

    assert scroll_commands({"x": 0, "y": -3}) == [("scroll", {"x": 0, "y": -3})]

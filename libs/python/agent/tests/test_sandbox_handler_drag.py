"""SandboxComputerHandler.drag must drive the real cua_sandbox Mouse API."""

from types import SimpleNamespace

import pytest

pytest.importorskip("cua_sandbox")

from cua_agent.computers.sandbox import SandboxComputerHandler  # noqa: E402
from cua_sandbox.interfaces.mouse import Mouse  # noqa: E402


class _RecordingTransport:
    def __init__(self):
        self.sent = []

    async def send(self, action, **params):
        self.sent.append((action, params))


def _handler():
    transport = _RecordingTransport()
    return SandboxComputerHandler(SimpleNamespace(mouse=Mouse(transport))), transport


@pytest.mark.asyncio
async def test_drag_along_path_moves_through_every_point():
    handler, transport = _handler()

    await handler.drag(path=[{"x": 10, "y": 20}, {"x": 30, "y": 40}, {"x": 50, "y": 60}])

    assert transport.sent == [
        ("mouse_down", {"x": 10, "y": 20, "button": "left"}),
        ("move_cursor", {"x": 30, "y": 40}),
        ("move_cursor", {"x": 50, "y": 60}),
        ("mouse_up", {"x": 50, "y": 60, "button": "left"}),
    ]


@pytest.mark.asyncio
async def test_drag_from_start_to_end_coordinates():
    handler, transport = _handler()

    await handler.drag(start_x=1, start_y=2, end_x=3, end_y=4)

    assert transport.sent == [
        ("mouse_down", {"x": 1, "y": 2, "button": "left"}),
        ("move_cursor", {"x": 3, "y": 4}),
        ("mouse_up", {"x": 3, "y": 4, "button": "left"}),
    ]

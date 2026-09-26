"""predict_click must scale 0..1000 coordinates by width on x and height on y."""

import base64
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image


def _png_b64(width: int, height: int) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (width, height)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _response(text: str):
    return SimpleNamespace(model_dump=lambda: {"choices": [{"message": {"content": text}}]})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name, config_name",
    [
        ("cua_agent.loops.generic_vlm", "GenericVlmConfig"),
        ("cua_agent.loops.qwen35", "Qwen35Config"),
    ],
)
async def test_predict_click_scales_x_by_width_and_y_by_height(module_name, config_name):
    import importlib

    module = importlib.import_module(module_name)
    config = getattr(module, config_name)()
    # 1920x1088 is already a multiple of 32, so smart_resize keeps it as is.
    text = '<tool_call>{"name": "computer_use", "arguments": {"action": "left_click", "coordinate": [500, 250]}}</tool_call>'
    with patch.object(module.litellm, "acompletion", AsyncMock(return_value=_response(text))):
        result = await config.predict_click(
            model="qwen3-vl", image_b64=_png_b64(1920, 1088), instruction="click"
        )

    assert result == (960, 272)

"""GTA1, Gelato and UI-Ins predict_click must return None when the model gives no coordinates.

Returning (0, 0) instead makes the composed loop click the top-left corner of the
screen and skip its retries, because (0, 0) is a truthy tuple.
"""

import base64
import importlib
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image


def _png_b64(width: int = 640, height: int = 480) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (width, height)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _response(text: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


LOOPS = [
    ("cua_agent.loops.gta1", "GTA1Config", "HelloKKMe/GTA1-7B", "(100, 200)"),
    ("cua_agent.loops.gelato", "GelatoConfig", "mlfoundations/Gelato-30B-A3B", "(100, 200)"),
    ("cua_agent.loops.uiins", "UIInsConfig", "Tongyi-MiA/UI-Ins-7B", "[100, 200]"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("module_name, config_name, model, click_text", LOOPS)
async def test_predict_click_returns_none_without_coordinates(
    module_name, config_name, model, click_text
):
    module = importlib.import_module(module_name)
    config = getattr(module, config_name)()
    reply = _response("I could not find that element on the screen.")
    with patch.object(module.litellm, "acompletion", AsyncMock(return_value=reply)):
        result = await config.predict_click(model=model, image_b64=_png_b64(), instruction="x")

    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize("module_name, config_name, model, click_text", LOOPS)
async def test_predict_click_still_returns_parsed_coordinates(
    module_name, config_name, model, click_text
):
    module = importlib.import_module(module_name)
    config = getattr(module, config_name)()
    reply = _response(click_text)
    # 644x476 is a multiple of 28 inside the pixel bounds, so no rescaling happens.
    with patch.object(module.litellm, "acompletion", AsyncMock(return_value=reply)):
        result = await config.predict_click(
            model=model, image_b64=_png_b64(644, 476), instruction="x"
        )

    assert result == (100, 200)

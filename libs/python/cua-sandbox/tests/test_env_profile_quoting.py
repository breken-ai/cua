"""Image.env() values must survive being sourced from /etc/profile.d/cua-env.sh.

The Docker and Lume runtimes and the QEMU image builder write each variable as an
``export`` line. These tests run the exact commands they send through a real
shell (with ``sudo`` dropped and the file redirected to a temp path), source the
result, and read the variables back.
"""

import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from cua_sandbox.image import Image
from cua_sandbox.runtime.base import RuntimeInfo

VALUES = {
    "GREETING": "hello world",
    "DATABASE_URL": "postgres://db/app?sslmode=require&connect_timeout=5",
    "PRICE": "$5 each",
    "QUOTED": 'it\'s "quoted"',
}


class _RecordingExecutor:
    commands: list = []

    def __init__(self, *args, **kwargs):
        pass

    async def run_command(self, command, timeout=None):
        _RecordingExecutor.commands.append(command)
        return {"success": True}

    async def execute_layers(self, layers):
        pass


def _replay_and_read(commands, tmp_path: Path) -> dict:
    profile = tmp_path / "cua-env.sh"
    for command in commands:
        command = command.replace("/etc/profile.d/cua-env.sh", str(profile))
        command = command.replace("echo lume | sudo -S tee", "tee").replace("sudo tee", "tee")
        subprocess.run(["/bin/sh", "-c", command], check=True)
    read_back = "; ".join(f'printf "%s\\0" "${k}"' for k in VALUES)
    out = subprocess.run(
        ["/bin/sh", "-c", f". {profile} >/dev/null 2>&1; {read_back}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return dict(zip(VALUES, out.split("\0")))


@pytest.fixture(autouse=True)
def _reset_commands():
    _RecordingExecutor.commands = []


@pytest.mark.asyncio
async def test_builder_env_profile_keeps_values(tmp_path):
    from cua_sandbox.builder.build import _apply_env

    await _apply_env(_RecordingExecutor(), Image.linux().env(**VALUES))

    assert _replay_and_read(_RecordingExecutor.commands, tmp_path) == VALUES


@pytest.mark.asyncio
async def test_lume_env_profile_keeps_values(tmp_path):
    from cua_sandbox.runtime.lume import LumeRuntime

    info = RuntimeInfo(host="localhost", api_port=8000, name="vm")
    with patch("cua_sandbox.builder.executor.LayerExecutor", _RecordingExecutor):
        await LumeRuntime()._apply_image_layers(Image.linux().env(**VALUES), info)

    assert _replay_and_read(_RecordingExecutor.commands, tmp_path) == VALUES


@pytest.mark.asyncio
async def test_docker_env_profile_keeps_values(tmp_path):
    from cua_sandbox.runtime import docker as docker_mod

    ran = subprocess.CompletedProcess(args=[], returncode=0, stdout="0123456789abcdef", stderr="")
    with (
        patch.object(docker_mod, "_has_docker", return_value=True),
        patch.object(docker_mod, "_docker_bin", return_value="docker"),
        patch.object(docker_mod, "_find_free_port", return_value=18000),
        patch.object(docker_mod.subprocess, "run", return_value=ran),
        patch.object(docker_mod.DockerRuntime, "is_ready", AsyncMock()),
        patch("cua_sandbox.builder.executor.LayerExecutor", _RecordingExecutor),
    ):
        await docker_mod.DockerRuntime().start(Image.linux().env(**VALUES), "sb")

    assert _replay_and_read(_RecordingExecutor.commands, tmp_path) == VALUES

"""Cross-platform CI smoke coverage for Recollectium service surfaces.

This helper exercises the installed bootstrap CLI, API service, and MCP service
in isolated temp state so the CI workflow can stay compact while still verifying
service lifecycle and memory operations on every matrix platform.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.types import TextContent

ROOT = Path(__file__).resolve().parents[1]
SERVICE_HOST = "127.0.0.1"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or args[0] not in {"api", "mcp"}:
        print("usage: ci_service_smoke.py [api|mcp]", file=sys.stderr)
        return 2

    service_type = args[0]
    with tempfile.TemporaryDirectory(
        prefix=f"recollectium-{service_type}-smoke-"
    ) as smoke_root:
        root = Path(smoke_root)
        if service_type == "api":
            _exercise_api_service(root)
        else:
            asyncio.run(_exercise_mcp_service(root))
    return 0


def _resolve_recollectium_command() -> list[str]:
    command = shutil.which("recollectium")
    if command:
        return [command]

    uv = shutil.which("uv")
    if uv:
        completed = _run_command([uv, "tool", "dir", "--bin"])
        executable = Path(completed.stdout.strip()) / (
            "recollectium.exe" if os.name == "nt" else "recollectium"
        )
        if executable.exists():
            return [str(executable)]

    tool_bin_dir = os.environ.get("UV_TOOL_BIN_DIR")
    if tool_bin_dir:
        executable = Path(tool_bin_dir) / (
            "recollectium.exe" if os.name == "nt" else "recollectium"
        )
        if executable.exists():
            return [str(executable)]

    raise RuntimeError(
        "recollectium executable was not found on PATH or in the uv tool bin directory"
    )


def _run_command(
    args: list[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(args)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed


def _run_json(args: list[str]) -> Any:
    completed = _run_command(args)
    if completed.stderr:
        raise RuntimeError(
            f"unexpected stderr from {' '.join(args)}:\n{completed.stderr}"
        )
    return json.loads(completed.stdout)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((SERVICE_HOST, 0))
        return sock.getsockname()[1]


def _configure_smoke_root(
    recollectium: list[str], config_path: Path, smoke_root: Path, port: int
) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    for key, value in (
        ("service.host", SERVICE_HOST),
        ("service.port", str(port)),
        ("directories.data", str(smoke_root / "data")),
        ("directories.cache", str(smoke_root / "cache")),
        ("directories.logs", str(smoke_root / "logs")),
        ("directories.runtime", str(smoke_root / "run")),
    ):
        _run_json(
            [
                *recollectium,
                "--config",
                str(config_path),
                "config",
                "set",
                key,
                value,
                "--json",
            ]
        )


def _assert_service_payloads(
    start_payload: dict[str, Any],
    status_payload: dict[str, Any],
    discover_payload: dict[str, Any],
    service_type: str,
) -> str:
    assert start_payload["status"] == "started", start_payload
    assert start_payload["type"] == service_type, start_payload
    assert isinstance(start_payload["pid"], int) and start_payload["pid"] > 0, (
        start_payload
    )

    assert status_payload["running"] is True, status_payload
    assert status_payload["type"] == service_type, status_payload
    assert isinstance(status_payload["pid"], int) and status_payload["pid"] > 0, (
        status_payload
    )
    assert status_payload["endpoint"].startswith("http://"), status_payload

    assert discover_payload["status"] == "running", discover_payload
    assert discover_payload["type"] == service_type, discover_payload
    assert isinstance(discover_payload["pid"], int) and discover_payload["pid"] > 0, (
        discover_payload
    )
    for key in ("endpoint", "health_url", "version_url", "capabilities_url"):
        value = discover_payload.get(key)
        assert isinstance(value, str) and value.startswith("http://"), discover_payload
    return status_payload["endpoint"]


def _wait_for_health(health_url: str) -> dict[str, Any]:
    deadline = time.monotonic() + 30
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=2) as response:
                assert response.status == 200, (health_url, response.status)
                payload = json.loads(response.read().decode("utf-8"))
            assert payload["data"]["status"] == "ok", payload
            return payload
        except Exception as exc:  # pragma: no cover - smoke retry
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"service health did not become ready: {last_error!r}")


def _request_json(
    method: str, url: str, body: dict[str, Any] | None = None
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 200, (method, url, response.status)
        return json.loads(response.read().decode("utf-8"))


def _exercise_api_service(root: Path) -> None:
    recollectium = _resolve_recollectium_command()
    config_path = root / "config" / "config.json"
    port = _free_port()
    _configure_smoke_root(recollectium, config_path, root, port)

    stop_payload: dict[str, Any] | None = None
    try:
        start_payload = _run_json(
            [
                *recollectium,
                "--config",
                str(config_path),
                "service",
                "start",
                "api",
                "--json",
            ]
        )
        status_payload = _run_json(
            [*recollectium, "--config", str(config_path), "service", "status", "--json"]
        )
        discover_payload = _run_json(
            [
                *recollectium,
                "--config",
                str(config_path),
                "service",
                "discover",
                "--json",
            ]
        )
        endpoint = _assert_service_payloads(
            start_payload, status_payload, discover_payload, "api"
        )

        _wait_for_health(discover_payload["health_url"])
        version = _request_json("GET", discover_payload["version_url"])
        assert version["data"]["service_api_version"] == "1", version
        assert isinstance(version["data"]["recollectium_version"], str), version
        capabilities = _request_json("GET", discover_payload["capabilities_url"])
        assert capabilities["data"]["service_api_version"] == "1", capabilities
        assert isinstance(capabilities["data"]["capabilities"], list), capabilities
        assert "health.read" in capabilities["data"]["capabilities"], capabilities

        user_add = _request_json(
            "POST",
            f"{endpoint}/v1/memories",
            {"space": "user", "type": "fact", "content": "CI API user memory"},
        )
        user_memory = user_add["data"]
        assert user_memory["status"] == "saved", user_memory
        user_id = user_memory["id"]

        user_search = _request_json(
            "POST",
            f"{endpoint}/v1/memories/search_user",
            {"query": "CI API user memory", "type": "fact"},
        )
        assert user_search["data"][0]["id"] == user_id, user_search

        user_get = _request_json("GET", f"{endpoint}/v1/memories/{user_id}")
        assert user_get["data"]["id"] == user_id, user_get
        assert user_get["data"]["content"] == "CI API user memory", user_get

        workspace_uid = "ci-service-smoke-workspace"
        workspace_add = _request_json(
            "POST",
            f"{endpoint}/v1/memories",
            {
                "space": "workspace",
                "workspace_uid": workspace_uid,
                "type": "decision",
                "content": "CI API workspace memory",
            },
        )
        workspace_memory = workspace_add["data"]
        assert workspace_memory["status"] == "saved", workspace_memory
        workspace_id = workspace_memory["id"]

        workspace_search = _request_json(
            "POST",
            f"{endpoint}/v1/memories/search_workspace",
            {
                "query": "CI API workspace memory",
                "workspace_uid": workspace_uid,
                "type": "decision",
            },
        )
        assert workspace_search["data"][0]["id"] == workspace_id, workspace_search

        workspace_get = _request_json("GET", f"{endpoint}/v1/memories/{workspace_id}")
        assert workspace_get["data"]["id"] == workspace_id, workspace_get
        assert workspace_get["data"]["content"] == "CI API workspace memory", (
            workspace_get
        )

        stop_result = _run_json(
            [*recollectium, "--config", str(config_path), "service", "stop", "--json"]
        )
        stopped_payload = _run_json(
            [*recollectium, "--config", str(config_path), "service", "status", "--json"]
        )
        assert stop_result["status"] == "stopped", stop_result
        assert stopped_payload["running"] is False, stopped_payload
        stop_payload = stop_result
    finally:
        if stop_payload is None:
            _run_command(
                [
                    *recollectium,
                    "--config",
                    str(config_path),
                    "service",
                    "stop",
                    "--json",
                ],
                check=False,
            )


async def _exercise_mcp_service(root: Path) -> None:
    recollectium = _resolve_recollectium_command()
    config_path = root / "config" / "config.json"
    port = _free_port()
    _configure_smoke_root(recollectium, config_path, root, port)

    stop_payload: dict[str, Any] | None = None
    try:
        start_payload = _run_json(
            [
                *recollectium,
                "--config",
                str(config_path),
                "service",
                "start",
                "mcp",
                "--json",
            ]
        )
        status_payload = _run_json(
            [*recollectium, "--config", str(config_path), "service", "status", "--json"]
        )
        discover_payload = _run_json(
            [
                *recollectium,
                "--config",
                str(config_path),
                "service",
                "discover",
                "--json",
            ]
        )
        endpoint = _assert_service_payloads(
            start_payload, status_payload, discover_payload, "mcp"
        )

        await _wait_for_mcp_ready(endpoint)

        stop_result = await _exercise_mcp_memory_round_trip(
            recollectium, config_path, endpoint
        )
        stopped_payload = _run_json(
            [*recollectium, "--config", str(config_path), "service", "status", "--json"]
        )
        assert stop_result["status"] == "stopped", stop_result
        assert stopped_payload["running"] is False, stopped_payload
        stop_payload = stop_result
    finally:
        if stop_payload is None:
            _run_command(
                [
                    *recollectium,
                    "--config",
                    str(config_path),
                    "service",
                    "stop",
                    "--json",
                ],
                check=False,
            )


async def _wait_for_mcp_ready(endpoint: str) -> None:
    deadline = time.monotonic() + 30
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            async with sse_client(f"{endpoint}/sse", timeout=5, sse_read_timeout=5) as (
                read_stream,
                write_stream,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    tool_names = {tool.name for tool in tools.tools}
                    assert {"add_memory", "get_memory", "search_user_memory"}.issubset(
                        tool_names
                    ), tools
                    return
        except Exception as exc:  # pragma: no cover - smoke retry
            last_error = exc
            await asyncio.sleep(1)
    raise RuntimeError(f"MCP service did not become ready: {last_error!r}")


async def _exercise_mcp_memory_round_trip(
    recollectium: list[str],
    config_path: Path,
    endpoint: str,
) -> dict[str, Any]:
    async with sse_client(f"{endpoint}/sse", timeout=5, sse_read_timeout=5) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            add_result = await session.call_tool(
                "add_memory",
                {"space": "user", "type": "fact", "content": "CI MCP user memory"},
            )
            assert not add_result.isError, add_result
            add_content = add_result.content[0]
            assert isinstance(add_content, TextContent), add_content
            added_memory = json.loads(add_content.text)
            assert added_memory["status"] == "saved", added_memory
            memory_id = added_memory["id"]

            search_result = await session.call_tool(
                "search_user_memory",
                {"query": "CI MCP user memory", "verbosity": "verbose"},
            )
            assert not search_result.isError, search_result
            search_content = search_result.content[0]
            assert isinstance(search_content, TextContent), search_content
            search_payload = json.loads(search_content.text)
            assert search_payload[0]["memory"]["id"] == memory_id, search_payload

            get_result = await session.call_tool(
                "get_memory",
                {"id": memory_id, "verbosity": "verbose"},
            )
            assert not get_result.isError, get_result
            get_content = get_result.content[0]
            assert isinstance(get_content, TextContent), get_content
            get_payload = json.loads(get_content.text)
            assert get_payload["id"] == memory_id, get_payload
            assert get_payload["content"] == "CI MCP user memory", get_payload

    stop_payload = _run_json(
        [*recollectium, "--config", str(config_path), "service", "stop", "--json"]
    )
    return stop_payload


if __name__ == "__main__":
    raise SystemExit(main())

"""GitHub workflow contract checks."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def _all_workflows_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(WORKFLOWS.glob("*.yml"))
    )


def test_all_workflows_parse_as_yaml() -> None:
    for path in sorted(WORKFLOWS.glob("*.yml")):
        assert yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_ci_format_check_stays_strict_and_prints_diagnostics() -> None:
    workflow = _workflow("ci.yml")

    assert "uv run ruff format --check ." in workflow
    assert "::error title=Ruff formatting check failed::" in workflow
    assert "uv run ruff format --diff . || true" in workflow
    assert 'exit "$status"' in workflow
    assert "continue-on-error" not in workflow


def test_ci_cancels_superseded_pr_runs_only() -> None:
    workflow = _workflow("ci.yml")

    assert "concurrency:" in workflow
    assert (
        "github.event_name == 'pull_request' && github.event.pull_request.number || github.run_id"
        in workflow
    )
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in workflow


def test_publish_pypi_workflow_uses_trusted_publishing_and_tag_check() -> None:
    workflow = _workflow("publish-pypi.yml")

    assert 'tags:\n      - "v*"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "required: true" in workflow
    assert "permissions:\n  contents: read\n  id-token: write" in workflow
    assert "environment: pypi" in workflow
    assert "actions/checkout@v6" in workflow
    assert "ref: ${{ steps.release_tag.outputs.tag }}" in workflow
    assert "actions/setup-python@v6" in workflow
    assert 'python-version: "3.12"' in workflow
    assert "python -m pip install uv==0.11.15" in workflow
    assert "pyproject.toml version" in workflow
    assert "uv build --sdist --wheel" in workflow
    assert "uvx --from twine twine check dist/*" in workflow
    assert "uv publish --trusted-publishing always dist/*" in workflow


def test_workflows_keep_expected_action_pins() -> None:
    workflow_pins = {
        "ci.yml": ("actions/checkout@v6", "actions/setup-python@v6"),
        "publish-pypi.yml": ("actions/checkout@v6", "actions/setup-python@v6"),
        "release.yml": ("actions/checkout@v6", "softprops/action-gh-release@v3"),
    }

    for workflow_name, expected_pins in workflow_pins.items():
        workflow = _workflow(workflow_name)
        for pin in expected_pins:
            assert pin in workflow

    workflows = _all_workflows_text()
    for legacy_pin in (
        "actions/checkout@v5",
        "actions/setup-python@v5",
        "softprops/action-gh-release@v2",
    ):
        assert legacy_pin not in workflows


def test_ci_service_smoke_script_covers_api_and_mcp_surfaces() -> None:
    script = (ROOT / "scripts" / "ci_service_smoke.py").read_text(encoding="utf-8")

    assert "def _exercise_api_service" in script
    assert "def _exercise_mcp_service" in script
    assert (
        '[\n                *recollectium,\n                "--config",\n                str(config_path),\n                "service",\n                "start",\n                "api",\n                "--json",\n            ]'
        in script
    )
    assert (
        '[\n                *recollectium,\n                "--config",\n                str(config_path),\n                "service",\n                "start",\n                "mcp",\n                "--json",\n            ]'
        in script
    )
    assert '"service", "stop", "--json"' in script
    assert '"service", "status", "--json"' in script
    assert '"service",\n                "discover",' in script
    assert "completed.returncode != 1" in script
    assert "_assert_not_running_discover_payload(post_stop_discover)" in script
    assert "search_workspace_memory" in script
    assert 'workspace_uid = "ci-service-smoke-workspace"' in script
    assert "/v1/memories" in script
    assert "/v1/memories/search_user" in script
    assert "/v1/memories/search_workspace" in script
    assert "search_user_memory" in script
    assert "search_workspace_memory" in script
    assert "get_memory" in script


def test_ci_service_smoke_workflow_keeps_required_gates_and_matrix() -> None:
    workflow = _workflow("ci.yml")

    assert "uv run ruff check ." in workflow
    assert "uv run pyright" in workflow
    assert "uv run pytest --cov=src/recollectium --cov-report=term-missing" in workflow
    assert "fail-fast: false" in workflow
    assert "linux-x86_64" in workflow
    assert "linux-arm64" in workflow
    assert "macos-intel" in workflow
    assert "macos-apple-silicon" in workflow
    assert "windows-x86_64" in workflow
    assert "windows-arm64" in workflow
    assert "scripts/ci_service_smoke.py api" in workflow
    assert "scripts/ci_service_smoke.py mcp" in workflow
    assert '$uv = Join-Path $env:LOCALAPPDATA "uv\\uv.exe"' in workflow
    assert "& $uv run python scripts/ci_service_smoke.py api" in workflow
    assert "& $uv run python scripts/ci_service_smoke.py mcp" in workflow
    assert "Verify service surface smoke on Unix" in workflow
    assert "Verify service surface smoke on Windows" in workflow
    assert "service start api" in workflow
    assert "service status --json" in workflow
    assert "service discover --json" in workflow
    assert "service stop --json" in workflow
    assert "paths-ignore" not in workflow
    assert "[skip ci]" not in workflow

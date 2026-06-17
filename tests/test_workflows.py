"""GitHub workflow contract checks."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


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


def test_workflows_use_node24_action_versions() -> None:
    ci = _workflow("ci.yml")
    release = _workflow("release.yml")
    combined = f"{ci}\n{release}"

    assert "actions/checkout@v6" in combined
    assert "actions/setup-python@v6" in ci
    assert "python -m pip install uv==0.11.15" in ci
    assert "softprops/action-gh-release@v3" in release

    assert "actions/checkout@v4" not in combined
    assert "actions/setup-python@v5" not in combined
    assert "astral-sh/setup-uv@" not in combined
    assert "softprops/action-gh-release@v2" not in combined


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


def test_ci_keeps_required_gates_and_matrix() -> None:
    workflow = _workflow("ci.yml")

    assert "uv run ruff check ." in workflow
    assert "uv run pyright" in workflow
    assert "uv run pytest --cov=src/recollectium --cov-report=term-missing" in workflow
    assert "fail-fast: false" in workflow
    assert "windows-11-arm" in workflow
    assert "ubuntu-24.04-arm" in workflow
    assert "paths-ignore" not in workflow
    assert "[skip ci]" not in workflow

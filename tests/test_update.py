"""Upgrade planning tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from recollectium.update import (
    CommandResult,
    InstallMetadata,
    MainRefInfo,
    ReleaseLookupError,
    ReleaseInfo,
    TargetSelectorError,
    TrackingTarget,
    UpdatePlan,
    _bootstrap_target_env,
    _command_for_method,
    _current_newer_than,
    _parse_tracking_target,
    _versions_equal,
    apply_update,
    build_update_plan,
    detect_install_method,
    load_install_metadata,
    normalize_version_selector,
    resolve_latest_for_target,
    resolve_main_ref,
    select_tracking_target,
    write_install_metadata_update,
)


class FakeRunner:
    def __init__(self, results: list[CommandResult] | None = None) -> None:
        self.results = results or [CommandResult(0, "ok", "")]
        self.calls: list[tuple[list[str], str | None]] = []

    def run(
        self, command: list[str], *, timeout_seconds: int, cwd: str | None = None
    ) -> CommandResult:
        self.calls.append((command, cwd))
        return self.results.pop(0)


def _metadata(method: str = "uv_tool", path: Path | None = None) -> InstallMetadata:
    return InstallMetadata(
        install_method=method,  # type: ignore[arg-type]
        source_ref=None,
        installed_at=None,
        metadata_path=path,
    )


def test_build_update_plan_reports_up_to_date() -> None:
    plan = build_update_plan(
        current_version="1.0.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="uv_tool",
        metadata=_metadata(),
    )

    assert plan.status == "up_to_date"
    assert plan.command is None


def test_build_update_plan_detects_newer_release() -> None:
    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="uv_tool",
        metadata=_metadata(),
    )

    assert plan.status == "update_available"
    assert plan.command == ["uv", "tool", "upgrade", "recollectium"]


def test_build_update_plan_force_builds_command_when_equal() -> None:
    plan = build_update_plan(
        current_version="1.0.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="pipx",
        metadata=_metadata("pipx"),
        force=True,
    )

    assert plan.status == "update_available"
    assert plan.command == ["pipx", "upgrade", "recollectium"]


def test_build_update_plan_rejects_unknown_method() -> None:
    plan = build_update_plan(
        current_version="1.0.0",
        latest_release=ReleaseInfo(version="2.0.0", tag="v2.0.0", url=None),
        install_method="unknown",
        metadata=_metadata("unknown"),
    )

    assert plan.status == "unsupported_install_method"
    assert plan.reason == "unknown_install_method"


def test_bootstrap_plan_uses_latest_tag_not_main() -> None:
    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="bootstrap",
        metadata=_metadata("bootstrap"),
        platform_name="Linux",
    )

    assert plan.command is not None
    assert "v1.0.0/install.sh" in plan.command[-1]
    assert "main/install.sh" not in plan.command[-1]


def test_main_fallback_requires_allow_main() -> None:
    blocked = build_update_plan(
        current_version="0.9.0",
        latest_release=None,
        install_method="bootstrap",
        metadata=_metadata("bootstrap"),
    )
    allowed = build_update_plan(
        current_version="0.9.0",
        latest_release=None,
        install_method="bootstrap",
        metadata=_metadata("bootstrap"),
        allow_main=True,
        platform_name="Linux",
    )

    assert blocked.status == "network_error"
    assert blocked.reason == "no_latest_release"
    assert allowed.latest_tag == "main"
    assert allowed.reason == "main_fallback_allowed"
    assert allowed.command is not None
    assert "main/install.sh" in allowed.command[-1]
    assert "RECOLLECTIUM_INSTALL_MAIN" in allowed.command[-1]
    assert "RECOLLECTIUM_INSTALL_VERSION" not in allowed.command[-1]


def test_source_checkout_builds_safe_command_sequence(tmp_path: Path) -> None:
    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="source",
        metadata=_metadata("source"),
        source_root=tmp_path,
    )

    assert plan.command == [
        ["git", "fetch", "--tags", "origin"],
        ["git", "checkout", "v1.0.0"],
        ["uv", "sync", "--group", "dev"],
    ]
    assert plan.cwd == str(tmp_path)


def test_source_checkout_dirty_tree_blocks_apply(tmp_path: Path) -> None:
    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="source",
        metadata=_metadata("source"),
        source_root=tmp_path,
    )
    runner = FakeRunner([CommandResult(0, " M file.py\n", "")])

    result = apply_update(plan, runner=runner)

    assert result.returncode == 1
    assert "source_checkout_dirty" in result.stderr
    assert runner.calls == [(["git", "status", "--porcelain"], str(tmp_path))]


def test_apply_update_returns_runner_output() -> None:
    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="uv_tool",
        metadata=_metadata(),
    )
    runner = FakeRunner([CommandResult(0, "upgraded", "")])

    result = apply_update(plan, runner=runner)

    assert result == CommandResult(0, "upgraded", "")
    assert runner.calls == [(["uv", "tool", "upgrade", "recollectium"], None)]


def test_apply_update_logs_runner_failure() -> None:
    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="uv_tool",
        metadata=_metadata(),
    )
    runner = FakeRunner([CommandResult(9, "", "upgrade failed")])

    result = apply_update(plan, runner=runner)

    assert result == CommandResult(9, "", "upgrade failed")
    assert runner.calls == [(["uv", "tool", "upgrade", "recollectium"], None)]


def test_load_install_metadata_reads_state_file(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    (state / "install.json").write_text(
        json.dumps(
            {
                "install_method": "bootstrap",
                "source_ref": "v1.0.0",
                "installed_at": "2026-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    metadata = load_install_metadata(state_dir=state)

    assert metadata.install_method == "bootstrap"
    assert metadata.source_ref == "v1.0.0"
    assert metadata.metadata_path == state / "install.json"


def test_detect_install_method_prefers_metadata_and_env() -> None:
    assert detect_install_method(_metadata("bootstrap"), env={}) == "bootstrap"
    assert (
        detect_install_method(
            _metadata("unknown"), env={"RECOLLECTIUM_INSTALL_METHOD": "pipx"}
        )
        == "pipx"
    )


def test_detect_install_method_identifies_tool_paths(monkeypatch) -> None:
    monkeypatch.setattr(
        "recollectium.update.find_source_checkout_root", lambda start: None
    )
    assert (
        detect_install_method(
            _metadata("unknown"),
            executable_path="/home/al/.local/pipx/venvs/recollectium/bin/python",
            env={},
        )
        == "pipx"
    )
    assert (
        detect_install_method(
            _metadata("unknown"),
            executable_path="/home/al/.local/share/uv/tools/recollectium/bin/python",
            env={},
        )
        == "uv_tool"
    )


def test_release_lookup_error_records_reason() -> None:
    from recollectium.update import ReleaseLookupError

    exc = ReleaseLookupError("missing", reason="no_latest_release")

    assert str(exc) == "missing"
    assert exc.reason == "no_latest_release"


def test_fetch_latest_release_delegates_to_client() -> None:
    from recollectium.update import fetch_latest_release

    class Client:
        def latest_release(self, repo: str) -> ReleaseInfo:
            assert repo == "owner/repo"
            return ReleaseInfo("1.2.3", "v1.2.3", "https://example.test")

    assert fetch_latest_release(Client(), repo="owner/repo") == ReleaseInfo(
        "1.2.3", "v1.2.3", "https://example.test"
    )


def test_load_install_metadata_defaults_to_unknown_for_missing_file(
    tmp_path: Path,
) -> None:
    metadata = load_install_metadata(state_dir=tmp_path)

    assert metadata.install_method == "unknown"
    assert metadata.metadata_path is None


def test_load_install_metadata_invalid_json_keeps_path(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    (state / "install.json").write_text("not-json", encoding="utf-8")

    metadata = load_install_metadata(state_dir=state)

    assert metadata.install_method == "unknown"
    assert metadata.metadata_path == state / "install.json"


def test_load_install_metadata_windows_default_uses_localappdata(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    state = tmp_path / "recollectium"
    state.mkdir()
    (state / "install.json").write_text(
        json.dumps({"install_method": "pip", "source_ref": 123, "installed_at": False}),
        encoding="utf-8",
    )

    metadata = load_install_metadata(platform_name="Windows")

    assert metadata.install_method == "pip"
    assert metadata.source_ref is None
    assert metadata.installed_at is None
    assert metadata.metadata_path == state / "install.json"


def test_detect_install_method_identifies_pip_path(monkeypatch) -> None:
    monkeypatch.setattr(
        "recollectium.update.find_source_checkout_root", lambda start: None
    )
    assert (
        detect_install_method(
            _metadata("unknown"),
            executable_path="/venv/lib/python3.12/site-packages/bin/python",
            env={},
        )
        == "pip"
    )


def test_detect_install_method_falls_back_to_unknown(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "recollectium.update.find_source_checkout_root", lambda start: None
    )

    assert (
        detect_install_method(
            _metadata("unknown"), executable_path="/tmp/python", env={}
        )
        == "unknown"
    )


def test_find_source_checkout_root_handles_valid_and_unreadable_pyproject(
    tmp_path: Path, monkeypatch
) -> None:
    from recollectium.update import find_source_checkout_root

    bad = tmp_path / "bad"
    child = bad / "child"
    child.mkdir(parents=True)
    (bad / ".git").mkdir()
    (bad / "pyproject.toml").write_text('name = "other"', encoding="utf-8")
    assert find_source_checkout_root(child) is None

    good = tmp_path / "good"
    nested = good / "a" / "b"
    nested.mkdir(parents=True)
    (good / ".git").mkdir()
    (good / "pyproject.toml").write_text('name = "recollectium"', encoding="utf-8")
    assert find_source_checkout_root(nested) == good

    real_read_text = Path.read_text

    def _raise_for_bad(path: Path, *args, **kwargs):
        if path == bad / "pyproject.toml":
            raise OSError("denied")
        return real_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _raise_for_bad)
    assert find_source_checkout_root(child) is None


def test_build_update_plan_handles_invalid_current_version() -> None:
    plan = build_update_plan(
        current_version="not-a-version",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="pip",
        metadata=_metadata("pip"),
    )

    assert plan.status == "unsupported_install_method"
    assert plan.reason == "could_not_parse_current_version"


def test_build_update_plan_pip_and_windows_bootstrap_commands() -> None:
    pip_plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="pip",
        metadata=_metadata("pip"),
    )
    windows_plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="bootstrap",
        metadata=_metadata("bootstrap"),
        platform_name="Windows",
    )

    assert pip_plan.command is not None
    assert pip_plan.command[-3:] == ["install", "--upgrade", "recollectium"]
    assert windows_plan.command is not None
    assert windows_plan.command[0] == "powershell"
    assert "v1.0.0/install.ps1" in windows_plan.command[-1]


def test_plan_to_dict_and_version_from_invalid_tag() -> None:
    from recollectium.update import GitHubReleaseClient, plan_to_dict

    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version=None, tag="not-a-version", url=None),
        install_method="pipx",
        metadata=_metadata("pipx"),
    )

    assert plan_to_dict(plan)["latest_tag"] == "not-a-version"
    assert GitHubReleaseClient.latest_release


def test_apply_update_no_command_and_missing_executable(monkeypatch) -> None:
    monkeypatch.setattr("recollectium.update.shutil.which", lambda executable: None)
    no_command = build_update_plan(
        current_version="1.0.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="pipx",
        metadata=_metadata("pipx"),
    )
    needs_command = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="pipx",
        metadata=_metadata("pipx"),
    )

    assert apply_update(no_command, runner=FakeRunner()) == CommandResult(0, "", "")
    missing = apply_update(needs_command, runner=FakeRunner())
    assert missing.returncode == 1
    assert "not available" in missing.stderr


def test_apply_update_returns_source_status_failure(tmp_path: Path) -> None:
    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="source",
        metadata=_metadata("source"),
        source_root=tmp_path,
    )
    runner = FakeRunner([CommandResult(2, "", "fatal")])

    assert apply_update(plan, runner=runner).stderr == "fatal"


def test_subprocess_command_runner_success_and_errors(
    monkeypatch, tmp_path: Path
) -> None:
    import subprocess
    from recollectium.update import SubprocessCommandRunner

    runner = SubprocessCommandRunner()

    success = runner.run(
        ["python", "-c", "print('ok')"], timeout_seconds=10, cwd=str(tmp_path)
    )
    assert success.returncode == 0
    assert success.stdout.strip() == "ok"

    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd=["cmd"], timeout=1, output=b"out", stderr=b"err"
        )

    monkeypatch.setattr("recollectium.update.subprocess.run", _timeout)
    timed_out = runner.run(["cmd"], timeout_seconds=1)
    assert timed_out == CommandResult(124, "out", "err")

    def _os_error(*args, **kwargs):
        raise OSError("nope")

    monkeypatch.setattr("recollectium.update.subprocess.run", _os_error)
    failed = runner.run(["cmd"], timeout_seconds=1)
    assert failed == CommandResult(1, "", "nope")


def test_github_release_client_success_and_errors(monkeypatch) -> None:
    from email.message import Message
    import json as json_module
    from urllib.error import HTTPError, URLError
    from recollectium.update import GitHubReleaseClient, ReleaseLookupError

    class Response:
        def __init__(self, payload: bytes) -> None:
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return self.payload

    captured_headers: dict[str, str] = {}

    def _success(request, timeout):
        captured_headers.update(dict(request.header_items()))
        return Response(
            json_module.dumps({"tag_name": "v1.2.3", "html_url": "url"}).encode()
        )

    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr("recollectium.update.urlopen", _success)
    release = GitHubReleaseClient().latest_release("owner/repo")
    assert release == ReleaseInfo("1.2.3", "v1.2.3", "url")
    assert captured_headers["Authorization"] == "Bearer test-token"

    monkeypatch.setattr(
        "recollectium.update.urlopen",
        lambda request, timeout: Response(json_module.dumps({"tag_name": ""}).encode()),
    )
    try:
        GitHubReleaseClient().latest_release("owner/repo")
    except ReleaseLookupError as exc:
        assert exc.reason == "invalid_release_payload"

    def _http_404(*args, **kwargs):
        raise HTTPError("url", 404, "missing", Message(), None)

    monkeypatch.setattr("recollectium.update.urlopen", _http_404)
    try:
        GitHubReleaseClient().latest_release("owner/repo")
    except ReleaseLookupError as exc:
        assert exc.reason == "no_latest_release"

    def _http_500(*args, **kwargs):
        raise HTTPError("url", 500, "broken", Message(), None)

    monkeypatch.setattr("recollectium.update.urlopen", _http_500)
    try:
        GitHubReleaseClient().latest_release("owner/repo")
    except ReleaseLookupError as exc:
        assert exc.reason == "github_http_error"

    def _url_error(*args, **kwargs):
        raise URLError("offline")

    monkeypatch.setattr("recollectium.update.urlopen", _url_error)
    try:
        GitHubReleaseClient().latest_release("owner/repo")
    except ReleaseLookupError as exc:
        assert exc.reason == "release_lookup_failed"


def test_load_install_metadata_non_windows_default_path(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "recollectium.update.user_state_dir", lambda appname: str(tmp_path)
    )

    metadata = load_install_metadata(platform_name="Linux")

    assert metadata.install_method == "unknown"


def test_load_install_metadata_unknown_method_in_file(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    (state / "install.json").write_text(
        json.dumps({"install_method": "weird"}), encoding="utf-8"
    )

    metadata = load_install_metadata(state_dir=state)

    assert metadata.install_method == "unknown"


def test_detect_install_method_ignores_source_checkout_cwd(
    tmp_path: Path, monkeypatch
) -> None:
    import recollectium.update as update_mod

    nested = tmp_path / "repo" / "nested"
    nested.mkdir(parents=True)
    (tmp_path / "repo" / ".git").mkdir()
    (tmp_path / "repo" / "pyproject.toml").write_text(
        'name = "recollectium"', encoding="utf-8"
    )
    monkeypatch.chdir(nested)
    outside_module = tmp_path / "not-source" / "update.py"
    outside_module.parent.mkdir()
    outside_module.write_text("", encoding="utf-8")
    monkeypatch.setattr(update_mod, "__file__", str(outside_module))

    detected = detect_install_method(
        _metadata("unknown"),
        executable_path="/venv/lib/python3.12/site-packages/bin/python",
        env={},
    )

    assert detected == "pip"


def test_detect_install_method_finds_source_checkout_from_module_path(
    tmp_path: Path, monkeypatch
) -> None:
    import recollectium.update as update_mod

    repo = tmp_path / "repo"
    module_file = repo / "src" / "recollectium" / "update.py"
    module_file.parent.mkdir(parents=True)
    module_file.write_text("", encoding="utf-8")
    (repo / ".git").mkdir()
    (repo / "pyproject.toml").write_text('name = "recollectium"', encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(update_mod, "__file__", str(module_file))

    assert (
        detect_install_method(
            _metadata("unknown"), executable_path="/tmp/python", env={}
        )
        == "source"
    )


def test_invalid_release_tag_returns_none_version() -> None:
    from recollectium.update import GitHubReleaseClient
    import json as json_module

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json_module.dumps({"tag_name": "not a version"}).encode()

    import recollectium.update as update_mod

    original = update_mod.urlopen
    update_mod.urlopen = lambda request, timeout: Response()
    try:
        release = GitHubReleaseClient().latest_release("owner/repo")
    finally:
        update_mod.urlopen = original

    assert release.version is None


def test_command_for_unknown_method_is_empty() -> None:
    from recollectium.update import _command_for_method

    assert _command_for_method(
        "unknown",
        latest_tag="v1",
        repo="owner/repo",
        platform_name="Linux",
        source_root=None,
    ) == ([], None)


def test_build_update_plan_rejects_unsafe_repo_and_ref() -> None:
    unsafe_repo_plan = build_update_plan(
        current_version="1.0.0",
        latest_release=ReleaseInfo(version="2.0.0", tag="v2.0.0", url=None),
        install_method="bootstrap",
        metadata=_metadata("bootstrap"),
        repo="owner/repo;touch-pwned",
    )
    assert unsafe_repo_plan.status == "unsupported_install_method"
    assert unsafe_repo_plan.reason == "invalid_repo"

    unsafe_ref_plan = build_update_plan(
        current_version="1.0.0",
        latest_release=ReleaseInfo(version="2.0.0", tag="v2.0.0;touch-pwned", url=None),
        install_method="bootstrap",
        metadata=_metadata("bootstrap"),
    )
    assert unsafe_ref_plan.status == "unsupported_install_method"
    assert unsafe_ref_plan.reason == "invalid_release_ref"
    assert unsafe_ref_plan.command is None


def test_source_plan_requires_recollectium_checkout(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "recollectium.update.find_source_checkout_root", lambda start: None
    )

    plan = build_update_plan(
        current_version="1.0.0",
        latest_release=ReleaseInfo(version="2.0.0", tag="v2.0.0", url=None),
        install_method="source",
        metadata=_metadata("source"),
        source_root=None,
    )

    assert plan.status == "update_failed"
    assert plan.reason == "source_checkout_not_found"
    assert plan.command is None


def test_detect_install_method_treats_venv_as_pip_outside_source_checkout(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "recollectium.update.find_source_checkout_root", lambda start: None
    )
    monkeypatch.setattr("recollectium.update.sys.prefix", "/tmp/project/.venv")
    monkeypatch.setattr("recollectium.update.sys.base_prefix", "/usr")

    assert detect_install_method(_metadata("unknown"), env={}) == "pip"


def test_fetch_latest_release_rejects_invalid_repo_before_client_call() -> None:
    from recollectium.update import ReleaseLookupError, fetch_latest_release

    class Client:
        def latest_release(self, repo: str) -> ReleaseInfo:
            raise AssertionError("client should not be called")

    try:
        fetch_latest_release(Client(), repo="owner/repo;touch-pwned")
    except ReleaseLookupError as exc:
        assert exc.reason == "invalid_repo"


def test_apply_source_plan_without_cwd_fails_safely() -> None:
    from recollectium.update import UpdatePlan

    plan = UpdatePlan(
        status="update_available",
        current_version="1.0.0",
        latest_version="2.0.0",
        latest_tag="v2.0.0",
        install_method="source",
        command=[["git", "pull", "--ff-only"], ["uv", "sync", "--group", "dev"]],
        reason="update_available",
        metadata_path=None,
        cwd=None,
    )

    result = apply_update(plan, runner=FakeRunner())

    assert result == CommandResult(1, "", "source checkout not found")


def test_select_tracking_target_cli_and_metadata() -> None:
    from recollectium.update import TrackingTarget, select_tracking_target

    latest, latest_source = select_tracking_target(
        _metadata(), version_selector="latest"
    )
    pinned, pinned_source = select_tracking_target(
        _metadata(), version_selector="1.2.3"
    )
    main, main_source = select_tracking_target(_metadata(), main=True)
    metadata_target, metadata_source = select_tracking_target(
        InstallMetadata(
            "bootstrap",
            "v1.2.0",
            None,
            None,
            tracking_target=TrackingTarget(
                "release",
                "v1.2.0",
                repo="Metadata/Repo",
                version="1.2.0",
                ref="v1.2.0",
            ),
        )
    )
    overridden_metadata_target, overridden_metadata_source = select_tracking_target(
        InstallMetadata(
            "bootstrap",
            "v1.2.0",
            None,
            None,
            tracking_target=TrackingTarget(
                "release",
                "v1.2.0",
                repo="Metadata/Repo",
                version="1.2.0",
                ref="v1.2.0",
            ),
        ),
        repo="Override/Repo",
    )

    assert (latest.kind, latest.selector, latest_source) == (
        "latest_release",
        "latest",
        "cli",
    )
    assert (
        pinned.kind,
        pinned.selector,
        pinned.version,
        pinned.ref,
        pinned_source,
    ) == (
        "release",
        "v1.2.3",
        "1.2.3",
        "v1.2.3",
        "cli",
    )
    assert (main.kind, main.ref, main_source) == ("main", "main", "cli")
    assert (
        metadata_target.kind,
        metadata_target.ref,
        metadata_target.repo,
        metadata_source,
    ) == (
        "release",
        "v1.2.0",
        "Metadata/Repo",
        "metadata",
    )
    assert (
        overridden_metadata_target.kind,
        overridden_metadata_target.ref,
        overridden_metadata_target.repo,
        overridden_metadata_source,
    ) == (
        "release",
        "v1.2.0",
        "Override/Repo",
        "metadata",
    )


def test_load_install_metadata_reads_tracking_target(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    (state / "install.json").write_text(
        json.dumps(
            {
                "metadata_version": 2,
                "install_method": "bootstrap",
                "source_ref": "v1.2.3",
                "source_ref_kind": "release",
                "source_repo": "owner/repo",
                "tracking_target": {
                    "kind": "release",
                    "selector": "v1.2.3",
                    "version": "1.2.3",
                    "ref": "v1.2.3",
                    "repo": "owner/repo",
                },
            }
        ),
        encoding="utf-8",
    )

    metadata = load_install_metadata(state_dir=state)

    assert metadata.metadata_version == 2
    assert metadata.source_ref_kind == "release"
    assert metadata.source_repo == "owner/repo"
    assert metadata.tracking_target is not None
    assert metadata.tracking_target.kind == "release"
    assert metadata.tracking_target.version == "1.2.3"


def test_pinned_metadata_plain_upgrade_noops_without_force_or_selector() -> None:
    from recollectium.update import TrackingTarget

    metadata = InstallMetadata(
        "uv_tool",
        "v1.2.3",
        None,
        None,
        tracking_target=TrackingTarget(
            "release", "v1.2.3", version="1.2.3", ref="v1.2.3"
        ),
    )

    plain = build_update_plan(
        current_version="1.2.3",
        latest_release=None,
        install_method="uv_tool",
        metadata=metadata,
    )
    forced = build_update_plan(
        current_version="1.2.3",
        latest_release=None,
        install_method="uv_tool",
        metadata=metadata,
        force=True,
    )

    assert plain.status == "up_to_date"
    assert plain.reason == "pinned_release_current"
    assert forced.status == "update_available"
    assert forced.command == ["uv", "tool", "install", "--force", "recollectium==1.2.3"]


def test_cli_selector_release_builds_pinned_command_and_metadata_update() -> None:
    import sys
    from recollectium.update import normalize_version_selector

    metadata_path = Path("/tmp/recollectium-install.json")
    plan = build_update_plan(
        current_version="2.0.0",
        latest_release=None,
        install_method="pip",
        metadata=_metadata("pip", metadata_path),
        target=normalize_version_selector("1.2.3"),
        target_source="cli",
    )

    assert plan.status == "update_available"
    assert plan.command == [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "recollectium==1.2.3",
    ]
    assert plan.will_update_metadata is True
    assert plan.metadata_update is not None
    assert plan.metadata_update["source_ref"] == "v1.2.3"
    assert plan.metadata_update["source_ref_kind"] == "release"
    assert plan.metadata_update["tracking_target"] == {
        "kind": "release",
        "selector": "v1.2.3",
        "repo": "AlfonsoDehesa/recollectium",
        "version": "1.2.3",
        "ref": "v1.2.3",
    }


def test_dry_run_and_check_plans_do_not_write_metadata() -> None:
    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="uv_tool",
        metadata=_metadata(),
        dry_run=True,
    )

    assert plan.status == "dry_run"
    assert plan.will_update_metadata is False
    assert plan.metadata_update is None


def test_write_install_metadata_update_preserves_existing_fields(
    tmp_path: Path,
) -> None:
    from recollectium.update import write_install_metadata_update

    metadata_path = tmp_path / "install.json"
    metadata_path.write_text(
        json.dumps(
            {"install_method": "uv_tool", "installed_at": "then", "custom": "keep"}
        ),
        encoding="utf-8",
    )
    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo("1.0.0", "v1.0.0", "https://example.test/v1.0.0"),
        install_method="uv_tool",
        metadata=_metadata("uv_tool", metadata_path),
    )

    written = write_install_metadata_update(plan)
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert written == metadata_path
    assert payload["custom"] == "keep"
    assert payload["metadata_version"] == 2
    assert payload["installed_at"] == "then"
    assert payload["source_ref"] == "v1.0.0"
    assert payload["source_ref_kind"] == "release"
    assert payload["tracking_target"]["kind"] == "latest_release"


def test_main_target_uses_main_without_release_lookup() -> None:
    from recollectium.update import TrackingTarget

    plan = build_update_plan(
        current_version="1.0.0",
        latest_release=None,
        install_method="bootstrap",
        metadata=_metadata("bootstrap"),
        platform_name="Linux",
        target=TrackingTarget("main", "main", ref="main"),
        target_source="cli",
    )

    assert plan.status == "update_available"
    assert plan.latest_tag == "main"
    assert plan.command is not None
    assert "main/install.sh" in plan.command[-1]
    assert "RECOLLECTIUM_INSTALL_MAIN='1'" in plan.command[-1]


def test_main_target_up_to_date_when_metadata_commit_matches_remote() -> None:
    commit = "a" * 40
    metadata = InstallMetadata(
        install_method="uv_tool",
        source_ref=commit,
        installed_at=None,
        metadata_path=None,
        source_ref_kind="main",
        tracking_target=TrackingTarget("main", "main", ref="main"),
        last_resolved_ref="main",
        last_resolved_commit=commit,
    )

    plan = build_update_plan(
        current_version="1.0.0",
        latest_release=None,
        install_method="uv_tool",
        metadata=metadata,
        target=TrackingTarget("main", "main", ref="main"),
        target_source="metadata",
        main_ref=MainRefInfo(remote_commit=commit),
    )

    assert plan.status == "up_to_date"
    assert plan.command is None
    assert plan.reason == "main_commit_current"
    assert plan.current_commit == commit
    assert plan.target_commit == commit


def test_main_target_plans_update_when_metadata_commit_is_behind() -> None:
    old_commit = "a" * 40
    new_commit = "b" * 40
    metadata = InstallMetadata(
        install_method="uv_tool",
        source_ref=old_commit,
        installed_at=None,
        metadata_path=None,
        source_ref_kind="main",
        tracking_target=TrackingTarget("main", "main", ref="main"),
        last_resolved_ref="main",
        last_resolved_commit=old_commit,
    )

    plan = build_update_plan(
        current_version="1.0.0",
        latest_release=None,
        install_method="uv_tool",
        metadata=metadata,
        target=TrackingTarget("main", "main", ref="main"),
        target_source="metadata",
        main_ref=MainRefInfo(remote_commit=new_commit),
    )

    assert plan.status == "update_available"
    assert plan.command == [
        "uv",
        "tool",
        "install",
        "--force",
        f"git+https://github.com/AlfonsoDehesa/recollectium.git@{new_commit}",
    ]
    assert plan.reason == "main_commit_behind"
    assert plan.current_commit == old_commit
    assert plan.target_commit == new_commit
    assert plan.metadata_update is not None
    assert plan.metadata_update["source_ref"] == new_commit
    last_resolved = plan.metadata_update["last_resolved"]
    assert isinstance(last_resolved, dict)
    assert last_resolved["ref"] == "main"
    assert last_resolved["commit"] == new_commit


def test_bootstrap_main_target_installs_resolved_commit_keeps_main_tracking() -> None:
    commit = "c" * 40

    plan = build_update_plan(
        current_version="1.0.0",
        latest_release=None,
        install_method="bootstrap",
        metadata=_metadata("bootstrap"),
        platform_name="Linux",
        target=TrackingTarget("main", "main", ref="main"),
        target_source="cli",
        main_ref=MainRefInfo(remote_commit=commit),
    )

    assert plan.command is not None
    assert f"/{commit}/install.sh" in plan.command[-1]
    assert "RECOLLECTIUM_INSTALL_MAIN='1'" in plan.command[-1]
    assert f"RECOLLECTIUM_INSTALL_RESOLVED_REF='{commit}'" in plan.command[-1]
    assert plan.target_ref == "main"
    assert plan.target_commit == commit
    assert plan.metadata_update is not None
    assert plan.metadata_update["source_ref"] == commit
    tracking_target = plan.metadata_update["tracking_target"]
    assert isinstance(tracking_target, dict)
    assert tracking_target["kind"] == "main"
    assert tracking_target["ref"] == "main"


def test_source_main_target_checkout_pins_resolved_commit(tmp_path: Path) -> None:
    commit = "d" * 40

    plan = build_update_plan(
        current_version="1.0.0",
        latest_release=None,
        install_method="source",
        metadata=_metadata("source"),
        source_root=tmp_path,
        target=TrackingTarget("main", "main", ref="main"),
        target_source="cli",
        main_ref=MainRefInfo(remote_commit=commit),
    )

    assert plan.command == [
        ["git", "fetch", "origin", "main"],
        ["git", "checkout", commit],
        ["uv", "sync", "--group", "dev"],
    ]
    assert plan.target_ref == "main"
    assert plan.target_commit == commit


def test_source_main_target_compares_local_head_to_remote() -> None:
    commit = "c" * 40
    plan = build_update_plan(
        current_version="1.0.0",
        latest_release=None,
        install_method="source",
        metadata=_metadata("source"),
        source_root=Path("/repo"),
        target=TrackingTarget("main", "main", ref="main"),
        target_source="cli",
        main_ref=MainRefInfo(remote_commit=commit, current_commit=commit),
    )

    assert plan.status == "up_to_date"
    assert plan.command is None
    assert plan.current_commit == commit
    assert plan.target_commit == commit


def test_resolve_main_ref_uses_ls_remote_for_non_source() -> None:
    commit = "d" * 40
    runner = FakeRunner([CommandResult(0, f"{commit}\trefs/heads/main\n", "")])

    main_ref = resolve_main_ref(
        repo="owner/repo", install_method="uv_tool", runner=runner
    )

    assert main_ref == MainRefInfo(remote_commit=commit)
    assert runner.calls == [
        (
            [
                "git",
                "ls-remote",
                "https://github.com/owner/repo.git",
                "refs/heads/main",
            ],
            None,
        )
    ]


def test_resolve_main_ref_fetches_source_without_checkout(tmp_path: Path) -> None:
    remote_commit = "e" * 40
    current_commit = "f" * 40
    runner = FakeRunner(
        [
            CommandResult(0, "", ""),
            CommandResult(0, f"{remote_commit}\n", ""),
            CommandResult(0, f"{current_commit}\n", ""),
        ]
    )

    main_ref = resolve_main_ref(
        repo="owner/repo",
        install_method="source",
        runner=runner,
        source_root=tmp_path,
    )

    assert main_ref == MainRefInfo(
        remote_commit=remote_commit, current_commit=current_commit
    )
    assert runner.calls == [
        (["git", "fetch", "origin", "main"], str(tmp_path)),
        (["git", "rev-parse", "FETCH_HEAD"], str(tmp_path)),
        (["git", "rev-parse", "HEAD"], str(tmp_path)),
    ]


def test_resolve_main_ref_uses_ls_remote_for_source_non_mutating(
    tmp_path: Path,
) -> None:
    remote_commit = "1" * 40
    current_commit = "2" * 40
    runner = FakeRunner(
        [
            CommandResult(0, f"{remote_commit}\trefs/heads/main\n", ""),
            CommandResult(0, f"{current_commit}\n", ""),
        ]
    )

    main_ref = resolve_main_ref(
        repo="owner/repo",
        install_method="source",
        runner=runner,
        source_root=tmp_path,
        non_mutating=True,
    )

    assert main_ref == MainRefInfo(
        remote_commit=remote_commit, current_commit=current_commit
    )
    assert runner.calls == [
        (
            [
                "git",
                "ls-remote",
                "https://github.com/owner/repo.git",
                "refs/heads/main",
            ],
            None,
        ),
        (["git", "rev-parse", "HEAD"], str(tmp_path)),
    ]
    assert all("fetch" not in command for command, _cwd in runner.calls)


def test_resolve_main_ref_reports_source_non_mutating_ls_remote_failure(
    tmp_path: Path,
) -> None:
    runner = FakeRunner([CommandResult(2, "", "offline")])

    try:
        resolve_main_ref(
            repo="owner/repo",
            install_method="source",
            runner=runner,
            source_root=tmp_path,
            non_mutating=True,
        )
    except ReleaseLookupError as exc:
        assert exc.reason == "main_lookup_failed"
        assert str(exc) == "offline"
    else:  # pragma: no cover - assertion guard
        raise AssertionError("non-mutating source lookup failure should fail")

    assert runner.calls == [
        (
            [
                "git",
                "ls-remote",
                "https://github.com/owner/repo.git",
                "refs/heads/main",
            ],
            None,
        )
    ]


def test_resolve_main_ref_rejects_invalid_repo() -> None:
    runner = FakeRunner()

    try:
        resolve_main_ref(repo="owner/../repo", install_method="uv_tool", runner=runner)
    except ReleaseLookupError as exc:
        assert exc.reason == "invalid_repo"
    else:  # pragma: no cover - assertion guard
        raise AssertionError("invalid repo should fail")

    assert runner.calls == []


def test_resolve_main_ref_reports_source_fetch_failure(tmp_path: Path) -> None:
    runner = FakeRunner([CommandResult(128, "", "fetch failed")])

    try:
        resolve_main_ref(
            repo="owner/repo",
            install_method="source",
            runner=runner,
            source_root=tmp_path,
        )
    except ReleaseLookupError as exc:
        assert exc.reason == "main_lookup_failed"
        assert str(exc) == "fetch failed"
    else:  # pragma: no cover - assertion guard
        raise AssertionError("fetch failure should fail")

    assert runner.calls == [(["git", "fetch", "origin", "main"], str(tmp_path))]


def test_resolve_main_ref_reports_source_remote_lookup_failure(
    tmp_path: Path,
) -> None:
    runner = FakeRunner(
        [
            CommandResult(0, "", ""),
            CommandResult(0, "not-a-commit\n", ""),
            CommandResult(1, "", "head unavailable"),
        ]
    )

    try:
        resolve_main_ref(
            repo="owner/repo",
            install_method="source",
            runner=runner,
            source_root=tmp_path,
        )
    except ReleaseLookupError as exc:
        assert exc.reason == "main_lookup_failed"
        assert str(exc) == "not-a-commit\n"
    else:  # pragma: no cover - assertion guard
        raise AssertionError("malformed remote commit should fail")

    assert runner.calls == [
        (["git", "fetch", "origin", "main"], str(tmp_path)),
        (["git", "rev-parse", "FETCH_HEAD"], str(tmp_path)),
        (["git", "rev-parse", "HEAD"], str(tmp_path)),
    ]


def test_resolve_main_ref_reports_ls_remote_failures() -> None:
    failed_runner = FakeRunner([CommandResult(2, "", "offline")])

    try:
        resolve_main_ref(
            repo="owner/repo", install_method="bootstrap", runner=failed_runner
        )
    except ReleaseLookupError as exc:
        assert exc.reason == "main_lookup_failed"
        assert str(exc) == "offline"
    else:  # pragma: no cover - assertion guard
        raise AssertionError("ls-remote failure should fail")

    malformed_runner = FakeRunner([CommandResult(0, "not-a-commit\n", "")])
    try:
        resolve_main_ref(
            repo="owner/repo", install_method="bootstrap", runner=malformed_runner
        )
    except ReleaseLookupError as exc:
        assert exc.reason == "main_lookup_failed"
        assert str(exc) == "Could not resolve remote main."
    else:  # pragma: no cover - assertion guard
        raise AssertionError("malformed ls-remote output should fail")


def test_main_target_rejects_malformed_remote_commit() -> None:
    plan = build_update_plan(
        current_version="1.0.0",
        latest_release=None,
        install_method="uv_tool",
        metadata=_metadata(),
        target=TrackingTarget("main", "main", ref="main"),
        target_source="cli",
        main_ref=MainRefInfo(remote_commit="not-a-commit"),
    )

    assert plan.status == "network_error"
    assert plan.reason == "main_lookup_failed"
    assert plan.target_ref == "main"


def test_source_checkout_apply_runs_command_sequence(
    tmp_path: Path, monkeypatch
) -> None:
    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="source",
        metadata=_metadata("source"),
        source_root=tmp_path,
    )
    monkeypatch.setattr(
        "recollectium.update.shutil.which", lambda executable: executable
    )
    runner = FakeRunner(
        [
            CommandResult(0, "", ""),
            CommandResult(0, "fetched\n", ""),
            CommandResult(0, "checked out\n", ""),
            CommandResult(0, "synced\n", ""),
        ]
    )

    result = apply_update(plan, runner=runner)

    assert result == CommandResult(0, "fetched\nchecked out\nsynced\n", "")
    assert runner.calls == [
        (["git", "status", "--porcelain"], str(tmp_path)),
        (["git", "fetch", "--tags", "origin"], str(tmp_path)),
        (["git", "checkout", "v1.0.0"], str(tmp_path)),
        (["uv", "sync", "--group", "dev"], str(tmp_path)),
    ]


def test_source_checkout_apply_returns_first_command_failure(
    tmp_path: Path, monkeypatch
) -> None:
    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="source",
        metadata=_metadata("source"),
        source_root=tmp_path,
    )
    monkeypatch.setattr(
        "recollectium.update.shutil.which", lambda executable: executable
    )
    runner = FakeRunner(
        [
            CommandResult(0, "", ""),
            CommandResult(42, "partial", "failed"),
        ]
    )

    result = apply_update(plan, runner=runner)

    assert result == CommandResult(42, "partial", "failed")
    assert runner.calls == [
        (["git", "status", "--porcelain"], str(tmp_path)),
        (["git", "fetch", "--tags", "origin"], str(tmp_path)),
    ]


def test_source_checkout_apply_reports_missing_executable(
    tmp_path: Path, monkeypatch
) -> None:
    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="source",
        metadata=_metadata("source"),
        source_root=tmp_path,
    )
    monkeypatch.setattr("recollectium.update.shutil.which", lambda executable: None)
    runner = FakeRunner([CommandResult(0, "", "")])

    result = apply_update(plan, runner=runner)

    assert result == CommandResult(1, "", "git is not available on PATH")
    assert runner.calls == [(["git", "status", "--porcelain"], str(tmp_path))]


class FakeReleaseClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def latest_release(self, repo: str) -> ReleaseInfo:
        self.calls.append(repo)
        return ReleaseInfo("2.0.0", "v2.0.0", "https://example.test/release")


def test_normalize_version_selector_rejects_invalid_values() -> None:
    try:
        normalize_version_selector("")
    except TargetSelectorError as exc:
        assert "cannot be empty" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("empty selector should fail")

    try:
        normalize_version_selector("main")
    except TargetSelectorError as exc:
        assert "--main" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("main selector should fail")

    try:
        normalize_version_selector("feature/branch")
    except TargetSelectorError as exc:
        assert "release version" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("unsafe selector should fail")

    try:
        normalize_version_selector("not-a-version")
    except TargetSelectorError as exc:
        assert "invalid release version" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("invalid version should fail")


def test_select_tracking_target_cli_metadata_and_default_paths() -> None:
    metadata = InstallMetadata(
        install_method="uv_tool",
        source_ref=None,
        installed_at=None,
        metadata_path=None,
        tracking_target=TrackingTarget(
            kind="release",
            selector="v1.2.3",
            repo="bad repo",
            version="1.2.3",
            ref="v1.2.3",
        ),
    )

    target, source = select_tracking_target(metadata, repo="Owner/Repo")
    assert source == "metadata"
    assert target.repo == "Owner/Repo"

    target, source = select_tracking_target(metadata, main=True, repo="Owner/Repo")
    assert (target.kind, source, target.ref) == ("main", "cli", "main")

    try:
        select_tracking_target(metadata, version_selector="latest", main=True)
    except TargetSelectorError as exc:
        assert "mutually exclusive" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("conflicting selectors should fail")

    target, source = select_tracking_target(_metadata(), repo="Owner/Repo")
    assert (target.kind, source, target.repo) == (
        "latest_release",
        "default",
        "Owner/Repo",
    )


def test_resolve_latest_only_fetches_for_latest_release() -> None:
    client = FakeReleaseClient()
    latest = resolve_latest_for_target(
        TrackingTarget(kind="latest_release", selector="latest", repo="Owner/Repo"),
        client=client,
    )
    assert latest == ReleaseInfo("2.0.0", "v2.0.0", "https://example.test/release")
    assert client.calls == ["Owner/Repo"]

    client.calls.clear()
    assert (
        resolve_latest_for_target(
            TrackingTarget(kind="main", selector="main", repo="Owner/Repo", ref="main"),
            client=client,
        )
        is None
    )
    assert client.calls == []


def test_build_update_plan_covers_defensive_target_branches(monkeypatch) -> None:
    invalid = build_update_plan(
        current_version="1.0.0",
        latest_release=None,
        install_method="uv_tool",
        metadata=_metadata(),
        target=TrackingTarget(kind="custom_ref", selector="bad", ref="bad..ref"),
    )
    assert invalid.status == "unsupported_install_method"
    assert invalid.reason == "invalid_release_ref"

    import recollectium.update as update_mod

    monkeypatch.setattr(update_mod, "find_source_checkout_root", lambda _path: None)
    missing_source = build_update_plan(
        current_version="1.0.0",
        latest_release=ReleaseInfo("2.0.0", "v2.0.0", None),
        install_method="source",
        metadata=_metadata("source"),
    )
    assert missing_source.status == "update_failed"
    assert missing_source.reason == "source_checkout_not_found"

    current_newer = build_update_plan(
        current_version="2.0.0",
        latest_release=None,
        install_method="uv_tool",
        metadata=InstallMetadata(
            "uv_tool",
            "v1.0.0",
            None,
            None,
            tracking_target=TrackingTarget(
                "release", "v1.0.0", version="1.0.0", ref="v1.0.0"
            ),
        ),
    )
    assert current_newer.status == "up_to_date"
    assert current_newer.reason == "target_drift_requires_force"

    unparsable_current = build_update_plan(
        current_version="not-version",
        latest_release=ReleaseInfo("2.0.0", "v2.0.0", None),
        install_method="uv_tool",
        metadata=_metadata(),
    )
    assert unparsable_current.status == "unsupported_install_method"
    assert unparsable_current.reason == "could_not_parse_current_version"


def test_parse_tracking_target_edge_cases() -> None:
    assert _parse_tracking_target(None) is None
    assert _parse_tracking_target({"kind": "bogus"}) is None
    latest_target = _parse_tracking_target(
        {"kind": "latest_release", "selector": "latest"}
    )
    assert latest_target is not None
    assert latest_target.kind == "latest_release"
    main_target = _parse_tracking_target({"kind": "main", "repo": "Owner/Repo"})
    assert main_target is not None
    assert main_target.ref == "main"
    release_target = _parse_tracking_target(
        {"kind": "release", "selector": "1.2.3", "repo": "Owner/Repo"}
    )
    assert release_target is not None
    assert release_target.ref == "v1.2.3"
    assert _parse_tracking_target({"kind": "release", "selector": "bad"}) is None
    custom_target = _parse_tracking_target({"kind": "custom_ref", "ref": "feature-x"})
    assert custom_target is not None
    assert custom_target.ref == "feature-x"
    assert _parse_tracking_target({"kind": "custom_ref", "ref": "bad..ref"}) is None


def test_command_generation_for_target_modes(tmp_path: Path) -> None:
    main_target = TrackingTarget(
        kind="main", selector="main", repo="Owner/Repo", ref="main"
    )
    release_target = TrackingTarget(
        kind="release",
        selector="v1.2.3",
        repo="Owner/Repo",
        version="1.2.3",
        ref="v1.2.3",
    )
    latest_target = TrackingTarget(
        kind="latest_release", selector="latest", repo="Owner/Repo"
    )

    assert _command_for_method(
        "pip",
        latest_tag="main",
        repo="Owner/Repo",
        platform_name=None,
        source_root=None,
        target=main_target,
    )[0] == [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "git+https://github.com/Owner/Repo.git@main",
    ]
    assert _command_for_method(
        "pipx",
        latest_tag="v1.2.3",
        repo="Owner/Repo",
        platform_name=None,
        source_root=None,
        target=release_target,
    )[0] == ["pipx", "install", "--force", "recollectium==1.2.3"]
    assert _command_for_method(
        "uv_tool",
        latest_tag="v9.9.9",
        repo="Owner/Repo",
        platform_name=None,
        source_root=None,
        target=latest_target,
    )[0] == ["uv", "tool", "upgrade", "recollectium"]
    assert _command_for_method(
        "source",
        latest_tag="main",
        repo="Owner/Repo",
        platform_name=None,
        source_root=tmp_path,
        target=main_target,
    ) == (
        [
            ["git", "fetch", "origin", "main"],
            ["git", "checkout", "main"],
            ["uv", "sync", "--group", "dev"],
        ],
        tmp_path,
    )
    windows_command = _command_for_method(
        "bootstrap",
        latest_tag="v1.2.3",
        repo="Owner/Repo",
        platform_name="Windows",
        source_root=None,
        target=release_target,
    )[0]
    assert windows_command is not None
    assert "install.ps1" in windows_command[-1]
    assert "RECOLLECTIUM_INSTALL_VERSION" in windows_command[-1]
    assert _command_for_method(
        "unknown",
        latest_tag="v1.2.3",
        repo="Owner/Repo",
        platform_name=None,
        source_root=None,
        target=release_target,
    ) == ([], None)


def test_bootstrap_env_and_version_helpers() -> None:
    assert _bootstrap_target_env(
        TrackingTarget("latest_release", "latest"), "v1.2.3"
    ) == {
        "RECOLLECTIUM_INSTALL_VERSION": "latest",
        "RECOLLECTIUM_INSTALL_RESOLVED_REF": "v1.2.3",
        "RECOLLECTIUM_INSTALL_TRACKING": "latest_release",
    }
    assert _bootstrap_target_env(TrackingTarget("release", "v1.2.3"), "v1.2.3") == {
        "RECOLLECTIUM_INSTALL_VERSION": "v1.2.3"
    }
    assert _bootstrap_target_env(TrackingTarget("main", "main"), "main") == {
        "RECOLLECTIUM_INSTALL_MAIN": "1",
        "RECOLLECTIUM_INSTALL_RESOLVED_REF": "main",
    }
    assert _bootstrap_target_env(
        TrackingTarget("custom_ref", "feature", ref="feature"), "feature"
    ) == {"RECOLLECTIUM_INSTALL_REF": "feature"}
    assert _versions_equal("1.0.0", None) is False
    assert _versions_equal("not-version", "1.0.0") is False
    assert _current_newer_than("not-version", "1.0.0") is False


def test_load_install_metadata_handles_non_object_payload(
    tmp_path: Path, monkeypatch
) -> None:
    state = tmp_path / "state"
    install_dir = state / "recollectium"
    install_dir.mkdir(parents=True)
    (install_dir / "install.json").write_text("[]", encoding="utf-8")
    monkeypatch.setenv("XDG_STATE_HOME", str(state))

    metadata = load_install_metadata(platform_name="linux")

    assert metadata.install_method == "unknown"
    assert metadata.metadata_path == install_dir / "install.json"


def test_build_update_plan_defensive_invalid_kind_and_command_none(monkeypatch) -> None:
    invalid_kind = build_update_plan(
        current_version="1.0.0",
        latest_release=None,
        install_method="uv_tool",
        metadata=_metadata(),
        target=TrackingTarget(kind="bogus", selector="bogus", ref="v1.0.0"),  # type: ignore[arg-type]
    )
    assert invalid_kind.status == "unsupported_install_method"
    assert invalid_kind.reason == "invalid_tracking_target"

    import recollectium.update as update_mod

    monkeypatch.setattr(
        update_mod, "_command_for_method", lambda *a, **kw: (None, None)
    )
    no_command = build_update_plan(
        current_version="1.0.0",
        latest_release=ReleaseInfo("2.0.0", "v2.0.0", None),
        install_method="uv_tool",
        metadata=_metadata(),
    )
    assert no_command.status == "unsupported_install_method"
    assert no_command.reason == "unsupported_target_for_install_method"


def test_custom_ref_current_and_metadata_write_edge_cases(tmp_path: Path) -> None:
    custom_current = build_update_plan(
        current_version="1.0.0",
        latest_release=None,
        install_method="bootstrap",
        metadata=InstallMetadata("bootstrap", "feature-x", None, None),
        target=TrackingTarget(kind="custom_ref", selector="feature-x", ref="feature-x"),
    )
    assert custom_current.status == "up_to_date"
    assert custom_current.reason == "custom_ref_current"

    assert write_install_metadata_update(custom_current) is None
    assert (
        write_install_metadata_update(
            UpdatePlan(
                "update_available",
                "1.0.0",
                "2.0.0",
                "v2.0.0",
                "uv_tool",
                ["uv", "tool", "upgrade", "recollectium"],
                None,
                None,
                will_update_metadata=True,
                metadata_update=None,
            ),
            platform_name="linux",
        )
        is None
    )

    metadata_path = tmp_path / "install.json"
    metadata_path.write_text("not-json", encoding="utf-8")
    payload_plan = build_update_plan(
        current_version="1.0.0",
        latest_release=ReleaseInfo("2.0.0", "v2.0.0", "https://example.test/release"),
        install_method="uv_tool",
        metadata=InstallMetadata("unknown", None, "old-date", metadata_path),
        force=True,
    )
    written = write_install_metadata_update(payload_plan)
    assert written == metadata_path
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["install_method"] == "uv_tool"
    assert payload["installed_at"] == "old-date"
    assert payload["last_resolved"]["release_url"] == "https://example.test/release"

    new_metadata_path = tmp_path / "fresh-install.json"
    fresh_plan = build_update_plan(
        current_version="1.0.0",
        latest_release=ReleaseInfo("2.0.0", "v2.0.0", None),
        install_method="uv_tool",
        metadata=InstallMetadata("uv_tool", None, None, new_metadata_path),
        force=True,
    )
    write_install_metadata_update(fresh_plan)
    fresh_payload = json.loads(new_metadata_path.read_text(encoding="utf-8"))
    assert "installed_at" in fresh_payload


def test_command_generation_fallbacks_and_windows_metadata_path(monkeypatch) -> None:
    assert _command_for_method(
        "pip",
        latest_tag="feature-x",
        repo="Owner/Repo",
        platform_name=None,
        source_root=None,
        target=TrackingTarget(kind="custom_ref", selector="feature-x", ref="feature-x"),
    )[0] == [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "git+https://github.com/Owner/Repo.git@feature-x",
    ]
    assert _command_for_method(
        "pipx",
        latest_tag="main",
        repo="Owner/Repo",
        platform_name=None,
        source_root=None,
        target=TrackingTarget(kind="main", selector="main", ref="main"),
    )[0] == ["pipx", "install", "--force", "git+https://github.com/Owner/Repo.git@main"]
    assert _command_for_method(
        "uv_tool",
        latest_tag="v1.2.3",
        repo="Owner/Repo",
        platform_name=None,
        source_root=None,
        target=TrackingTarget(kind="release", selector="latest", ref="v1.2.3"),
    )[0] == [
        "uv",
        "tool",
        "install",
        "--force",
        "git+https://github.com/Owner/Repo.git@v1.2.3",
    ]
    assert (
        _command_for_method(
            "source",
            latest_tag="v1.2.3",
            repo="Owner/Repo",
            platform_name=None,
            source_root=None,
            target=TrackingTarget(kind="release", selector="v1.2.3", ref="v1.2.3"),
        )[1]
        is not None
    )

    monkeypatch.setenv("LOCALAPPDATA", "C:/Users/A/AppData/Local")
    import recollectium.update as update_mod

    assert str(update_mod._default_metadata_path("Windows")).endswith(
        "recollectium/install.json"
    )

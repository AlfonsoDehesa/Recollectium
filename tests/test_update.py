"""Upgrade planning tests."""

from __future__ import annotations

import json
from pathlib import Path

from recollectium.update import (
    CommandResult,
    InstallMetadata,
    ReleaseInfo,
    apply_update,
    build_update_plan,
    detect_install_method,
    load_install_metadata,
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


def test_source_checkout_builds_safe_command_sequence(tmp_path: Path) -> None:
    plan = build_update_plan(
        current_version="0.9.0",
        latest_release=ReleaseInfo(version="1.0.0", tag="v1.0.0", url=None),
        install_method="source",
        metadata=_metadata("source"),
        source_root=tmp_path,
    )

    assert plan.command == [
        ["git", "pull", "--ff-only"],
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


def test_detect_install_method_finds_source_checkout_from_cwd(
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

    assert (
        detect_install_method(
            _metadata("unknown"), executable_path="/tmp/python", env={}
        )
        == "source"
    )


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
            CommandResult(0, "pulled\n", ""),
            CommandResult(0, "synced\n", ""),
        ]
    )

    result = apply_update(plan, runner=runner)

    assert result == CommandResult(0, "pulled\nsynced\n", "")
    assert runner.calls == [
        (["git", "status", "--porcelain"], str(tmp_path)),
        (["git", "pull", "--ff-only"], str(tmp_path)),
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
        (["git", "pull", "--ff-only"], str(tmp_path)),
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

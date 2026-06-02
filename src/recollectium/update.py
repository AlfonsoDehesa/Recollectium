"""Package upgrade planning and execution for Recollectium."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
import platform
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Literal, Protocol, TypeGuard
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from packaging.version import InvalidVersion, Version
from platformdirs import user_state_dir

import logging

_log = logging.getLogger(__name__)

InstallMethod = Literal["bootstrap", "pip", "pipx", "uv_tool", "source", "unknown"]
TargetKind = Literal["latest_release", "release", "main", "custom_ref", "unknown"]
TargetSource = Literal["cli", "metadata", "default"]
CommandSpec = list[str] | list[list[str]]
UpdateStatus = Literal[
    "up_to_date",
    "update_available",
    "updated",
    "dry_run",
    "unsupported_install_method",
    "network_error",
    "update_failed",
]

_INSTALL_METHODS = {"bootstrap", "pip", "pipx", "uv_tool", "source"}
_TARGET_KINDS = {"latest_release", "release", "main", "custom_ref"}
_DEFAULT_REPO = "AlfonsoDehesa/recollectium"
_GITHUB_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SAFE_REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


class UpdateError(Exception):
    """Base class for upgrade flow errors."""


class ReleaseLookupError(UpdateError):
    """Raised when latest release lookup fails."""

    def __init__(self, message: str, *, reason: str = "release_lookup_failed") -> None:
        super().__init__(message)
        self.reason = reason


class TargetSelectorError(UpdateError):
    """Raised when an upgrade selector is invalid."""


@dataclass(frozen=True)
class TrackingTarget:
    kind: TargetKind
    selector: str | None
    repo: str = _DEFAULT_REPO
    version: str | None = None
    ref: str | None = None


@dataclass(frozen=True)
class InstallMetadata:
    install_method: InstallMethod
    source_ref: str | None
    installed_at: str | None
    metadata_path: Path | None
    metadata_version: int = 1
    source_ref_kind: str | None = None
    source_repo: str | None = None
    tracking_target: TrackingTarget | None = None
    last_resolved_ref: str | None = None
    last_resolved_commit: str | None = None


@dataclass(frozen=True)
class ReleaseInfo:
    version: str | None
    tag: str
    url: str | None


@dataclass(frozen=True)
class UpdatePlan:
    status: UpdateStatus
    current_version: str
    latest_version: str | None
    latest_tag: str | None
    install_method: InstallMethod
    command: CommandSpec | None
    reason: str | None
    metadata_path: str | None
    cwd: str | None = None
    target_kind: TargetKind = "latest_release"
    target_selector: str | None = "latest"
    target_ref: str | None = None
    target_version: str | None = None
    target_source: TargetSource = "default"
    will_update_metadata: bool = False
    metadata_update: dict[str, object] | None = None
    current_commit: str | None = None
    target_commit: str | None = None


@dataclass(frozen=True)
class MainRefInfo:
    """Resolved main branch state used for commit-aware update checks."""

    remote_commit: str
    current_commit: str | None = None


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def run(
        self, command: list[str], *, timeout_seconds: int, cwd: str | None = None
    ) -> CommandResult: ...


class ReleaseClient(Protocol):
    def latest_release(self, repo: str) -> ReleaseInfo: ...


class GitHubReleaseClient:
    """Fetch latest release metadata from GitHub's REST API."""

    def latest_release(self, repo: str) -> ReleaseInfo:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "recollectium",
        }
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(
            f"https://api.github.com/repos/{repo}/releases/latest",
            headers=headers,
        )
        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                raise ReleaseLookupError(
                    "No latest GitHub release found.", reason="no_latest_release"
                ) from exc
            raise ReleaseLookupError(str(exc), reason="github_http_error") from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise ReleaseLookupError(str(exc)) from exc

        tag = payload.get("tag_name")
        if not isinstance(tag, str) or not tag:
            raise ReleaseLookupError(
                "Latest GitHub release did not include tag_name.",
                reason="invalid_release_payload",
            )
        return ReleaseInfo(
            version=_version_from_tag(tag), tag=tag, url=payload.get("html_url")
        )


class SubprocessCommandRunner:
    """Run package-manager commands with captured output."""

    def run(
        self, command: list[str], *, timeout_seconds: int, cwd: str | None = None
    ) -> CommandResult:
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = (
                exc.stdout.decode("utf-8", errors="replace")
                if isinstance(exc.stdout, bytes)
                else (exc.stdout or "")
            )
            stderr = (
                exc.stderr.decode("utf-8", errors="replace")
                if isinstance(exc.stderr, bytes)
                else (
                    exc.stderr or f"command timed out after {timeout_seconds} seconds"
                )
            )
            return CommandResult(returncode=124, stdout=stdout, stderr=stderr)
        except OSError as exc:
            return CommandResult(returncode=1, stdout="", stderr=str(exc))
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def load_install_metadata(
    *, state_dir: Path | None = None, platform_name: str | None = None
) -> InstallMetadata:
    """Read bootstrap install metadata when present."""
    if state_dir is None:
        if (platform_name or platform.system()).lower().startswith("win"):
            local_app_data = os.environ.get("LOCALAPPDATA")
            state_dir = (
                Path(local_app_data) / "recollectium"
                if local_app_data
                else Path(user_state_dir("recollectium"))
            )
        else:
            state_dir = Path(user_state_dir("recollectium"))
    metadata_path = state_dir / "install.json"
    if not metadata_path.exists():
        return InstallMetadata("unknown", None, None, None)

    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return InstallMetadata("unknown", None, None, metadata_path)
    if not isinstance(payload, dict):
        return InstallMetadata("unknown", None, None, metadata_path)
    method = payload.get("install_method")
    if method not in _INSTALL_METHODS:
        method = "unknown"
    source_ref = payload.get("source_ref")
    installed_at = payload.get("installed_at")
    metadata_version = payload.get("metadata_version")
    source_ref_kind = payload.get("source_ref_kind")
    source_repo = payload.get("source_repo")
    last_resolved = payload.get("last_resolved")
    last_resolved_ref = None
    last_resolved_commit = None
    if isinstance(last_resolved, dict):
        raw_ref = last_resolved.get("ref")
        raw_commit = last_resolved.get("commit")
        last_resolved_ref = raw_ref if isinstance(raw_ref, str) else None
        last_resolved_commit = raw_commit if isinstance(raw_commit, str) else None
    return InstallMetadata(
        install_method=method,  # type: ignore[arg-type]
        source_ref=source_ref if isinstance(source_ref, str) else None,
        installed_at=installed_at if isinstance(installed_at, str) else None,
        metadata_path=metadata_path,
        metadata_version=metadata_version if isinstance(metadata_version, int) else 1,
        source_ref_kind=source_ref_kind if isinstance(source_ref_kind, str) else None,
        source_repo=source_repo if isinstance(source_repo, str) else None,
        tracking_target=_parse_tracking_target(
            payload.get("tracking_target"), source_repo
        ),
        last_resolved_ref=last_resolved_ref,
        last_resolved_commit=last_resolved_commit,
    )


def detect_install_method(
    metadata: InstallMetadata,
    *,
    executable_path: str | None = None,
    env: dict[str, str] | None = None,
) -> InstallMethod:
    """Return bootstrap from metadata, else inspect module and executable paths."""
    if metadata.install_method != "unknown":
        return metadata.install_method

    env_map = os.environ if env is None else env
    override = env_map.get("RECOLLECTIUM_INSTALL_METHOD")
    if override in _INSTALL_METHODS:
        return override  # type: ignore[return-value]

    module_source_root = find_source_checkout_root(Path(__file__).resolve())
    if module_source_root is not None:
        return "source"

    path = (executable_path or sys.executable).replace("\\", "/").lower()
    if "/pipx/venvs/recollectium/" in path or "/pipx/" in path:
        return "pipx"
    if "/uv/tools/recollectium/" in path or "/uv/tool/" in path:
        return "uv_tool"
    if "/site-packages/" in path or "/dist-packages/" in path:
        return "pip"

    if executable_path is None and sys.prefix != getattr(
        sys, "base_prefix", sys.prefix
    ):
        return "pip"
    return "unknown"


def fetch_latest_release(
    client: ReleaseClient, *, repo: str = _DEFAULT_REPO
) -> ReleaseInfo:
    """Return the latest GitHub release as normalized version/tag data."""
    if not is_safe_github_repo(repo):
        raise ReleaseLookupError(
            "Invalid GitHub repository path.", reason="invalid_repo"
        )
    release = client.latest_release(repo)
    _log.info(
        "Fetched latest release",
        extra={
            "event": "update.release_fetched",
            "context": {"repo": repo, "tag": release.tag, "version": release.version},
        },
    )
    return release


def resolve_main_ref(
    *,
    repo: str = _DEFAULT_REPO,
    install_method: InstallMethod,
    runner: CommandRunner,
    source_root: Path | None = None,
    timeout_seconds: int = 60,
    non_mutating: bool = False,
) -> MainRefInfo:
    """Resolve remote main to a commit SHA, with local HEAD for source installs."""
    if not is_safe_github_repo(repo):
        raise ReleaseLookupError(
            "Invalid GitHub repository path.", reason="invalid_repo"
        )
    if install_method == "source" and source_root is not None and not non_mutating:
        fetch = runner.run(
            ["git", "fetch", "origin", "main"],
            timeout_seconds=timeout_seconds,
            cwd=str(source_root),
        )
        if fetch.returncode != 0:
            raise ReleaseLookupError(
                fetch.stderr or fetch.stdout, reason="main_lookup_failed"
            )
        remote = runner.run(
            ["git", "rev-parse", "FETCH_HEAD"],
            timeout_seconds=timeout_seconds,
            cwd=str(source_root),
        )
        current = runner.run(
            ["git", "rev-parse", "HEAD"],
            timeout_seconds=timeout_seconds,
            cwd=str(source_root),
        )
        remote_commit = _parse_commit_sha(remote.stdout)
        current_commit = (
            _parse_commit_sha(current.stdout) if current.returncode == 0 else None
        )
        if remote.returncode != 0 or remote_commit is None:
            raise ReleaseLookupError(
                remote.stderr or remote.stdout, reason="main_lookup_failed"
            )
        return MainRefInfo(remote_commit=remote_commit, current_commit=current_commit)

    result = runner.run(
        [
            "git",
            "ls-remote",
            f"https://github.com/{repo}.git",
            "refs/heads/main",
        ],
        timeout_seconds=timeout_seconds,
    )
    if result.returncode != 0:
        raise ReleaseLookupError(
            result.stderr or result.stdout, reason="main_lookup_failed"
        )
    commit = _parse_commit_sha(result.stdout)
    if commit is None:
        raise ReleaseLookupError(
            "Could not resolve remote main.", reason="main_lookup_failed"
        )
    if install_method == "source" and source_root is not None:
        current = runner.run(
            ["git", "rev-parse", "HEAD"],
            timeout_seconds=timeout_seconds,
            cwd=str(source_root),
        )
        current_commit = (
            _parse_commit_sha(current.stdout) if current.returncode == 0 else None
        )
        return MainRefInfo(remote_commit=commit, current_commit=current_commit)
    return MainRefInfo(remote_commit=commit)


def normalize_version_selector(selector: str) -> TrackingTarget:
    """Normalize an upgrade --version selector."""
    raw = selector.strip()
    if not raw:
        raise TargetSelectorError("--version cannot be empty")
    if raw.lower() == "latest":
        return TrackingTarget(kind="latest_release", selector="latest")
    if raw.lower() == "main":
        raise TargetSelectorError(
            "use --main to track the main branch; --version main is not supported"
        )
    normalized = raw[1:] if raw.startswith("v") else raw
    if any(token in raw for token in ("/", "\\", "://", "..", "@{")):
        raise TargetSelectorError("release version must be a version or v-prefixed tag")
    try:
        version = str(Version(normalized).public)
    except InvalidVersion as exc:
        raise TargetSelectorError(f"invalid release version: {selector}") from exc
    ref = f"v{version}"
    return TrackingTarget(kind="release", selector=ref, version=version, ref=ref)


def select_tracking_target(
    metadata: InstallMetadata,
    *,
    version_selector: str | None = None,
    main: bool = False,
    repo: str = _DEFAULT_REPO,
) -> tuple[TrackingTarget, TargetSource]:
    """Return the selected target and whether it came from CLI, metadata, or default."""
    if main and version_selector is not None:
        raise TargetSelectorError("--version and --main are mutually exclusive")
    if main:
        return TrackingTarget(
            kind="main", selector="main", repo=repo, ref="main"
        ), "cli"
    if version_selector is not None:
        target = normalize_version_selector(version_selector)
        return _target_with_repo(target, repo), "cli"
    if metadata.tracking_target is not None:
        target = metadata.tracking_target
        if repo != _DEFAULT_REPO or not is_safe_github_repo(target.repo):
            target = TrackingTarget(
                kind=target.kind,
                selector=target.selector,
                repo=repo,
                version=target.version,
                ref=target.ref,
            )
        return target, "metadata"
    return TrackingTarget(
        kind="latest_release", selector="latest", repo=repo
    ), "default"


def resolve_latest_for_target(
    target: TrackingTarget,
    *,
    client: ReleaseClient,
    repo_override: str | None = None,
) -> ReleaseInfo | None:
    """Fetch latest release only when the target requires it."""
    repo = repo_override or target.repo or _DEFAULT_REPO
    if target.kind == "latest_release":
        return fetch_latest_release(client, repo=repo)
    return None


def build_update_plan(
    *,
    current_version: str,
    latest_release: ReleaseInfo | None,
    install_method: InstallMethod,
    metadata: InstallMetadata,
    force: bool = False,
    dry_run: bool = False,
    allow_main: bool = False,
    repo: str = _DEFAULT_REPO,
    platform_name: str | None = None,
    source_root: Path | None = None,
    target: TrackingTarget | None = None,
    target_source: TargetSource = "default",
    main_ref: MainRefInfo | None = None,
) -> UpdatePlan:
    """Compare versions and return the exact update command or no-op state."""
    metadata_path = str(metadata.metadata_path) if metadata.metadata_path else None
    if target is None:
        target, target_source = select_tracking_target(metadata, repo=repo)
    selected_target = target

    repo = selected_target.repo or repo
    common = {
        "current_version": current_version,
        "install_method": install_method,
        "metadata_path": metadata_path,
        "target_kind": selected_target.kind,
        "target_selector": selected_target.selector,
        "target_source": target_source,
    }
    _log.info(
        "Building update plan",
        extra={
            "event": "update.plan_building",
            "context": common | {"dry_run": dry_run},
        },
    )

    def make_plan(
        status: UpdateStatus,
        *,
        latest_version: str | None = None,
        latest_tag: str | None = None,
        command: CommandSpec | None = None,
        reason: str | None = None,
        cwd: str | None = None,
        target_ref: str | None = None,
        target_version: str | None = None,
        will_update_metadata: bool = False,
        current_commit: str | None = None,
        target_commit: str | None = None,
    ) -> UpdatePlan:
        metadata_update = None
        if will_update_metadata:
            metadata_update = metadata_update_payload(
                metadata=metadata,
                install_method=install_method,
                target=selected_target,
                resolved_ref=target_ref or latest_tag,
                resolved_version=target_version or latest_version,
                release_url=latest_release.url if latest_release else None,
                repo=repo,
                resolved_commit=target_commit,
            )
        return UpdatePlan(
            status,
            current_version,
            latest_version,
            latest_tag,
            install_method,
            command,
            reason,
            metadata_path,
            cwd=cwd,
            target_kind=selected_target.kind,
            target_selector=selected_target.selector,
            target_ref=target_ref or latest_tag,
            target_version=target_version or latest_version,
            target_source=target_source,
            will_update_metadata=will_update_metadata,
            metadata_update=metadata_update,
            current_commit=current_commit,
            target_commit=target_commit,
        )

    if install_method == "unknown":
        return make_plan("unsupported_install_method", reason="unknown_install_method")
    if not is_safe_github_repo(repo):
        return make_plan("unsupported_install_method", reason="invalid_repo")

    latest_tag: str | None
    latest_version: str | None
    used_main_fallback = False
    if selected_target.kind == "latest_release":
        latest_tag = latest_release.tag if latest_release else None
        latest_version = latest_release.version if latest_release else None
        if latest_tag is None:
            if allow_main and install_method in {"bootstrap", "source"}:
                selected_target = TrackingTarget(
                    kind="main", selector="main", repo=repo, ref="main"
                )
                latest_tag = "main"
                latest_version = None
                used_main_fallback = True
            else:
                return make_plan("network_error", reason="no_latest_release")
    elif selected_target.kind in {"release", "main", "custom_ref"}:
        latest_tag = selected_target.ref
        latest_version = selected_target.version
    else:
        return make_plan("unsupported_install_method", reason="invalid_tracking_target")

    if latest_tag is None or not is_safe_ref(latest_tag):
        return make_plan(
            "unsupported_install_method",
            latest_version=latest_version,
            latest_tag=latest_tag,
            reason="invalid_release_ref",
        )

    if install_method == "source" and source_root is None:
        source_root = find_source_checkout_root(Path(__file__).resolve())
        if source_root is None:
            return make_plan(
                "update_failed",
                latest_version=latest_version,
                latest_tag=latest_tag,
                reason="source_checkout_not_found",
                target_ref=latest_tag,
                target_version=latest_version,
            )

    if selected_target.kind == "main":
        remote_commit = main_ref.remote_commit if main_ref else None
        current_commit = (
            main_ref.current_commit
            if main_ref and main_ref.current_commit
            else _installed_main_commit(metadata)
        )
        if remote_commit is not None and not is_commit_sha(remote_commit):
            return make_plan(
                "network_error",
                latest_version=latest_version,
                latest_tag=latest_tag,
                reason="main_lookup_failed",
                target_ref=latest_tag,
            )
        if remote_commit is not None and current_commit == remote_commit and not force:
            return make_plan(
                "up_to_date",
                latest_version=latest_version,
                latest_tag=latest_tag,
                reason="main_commit_current",
                target_ref=latest_tag,
                current_commit=current_commit,
                target_commit=remote_commit,
            )
    if selected_target.kind == "release" and not force:
        installed_on_pin = metadata.source_ref == latest_tag and _versions_equal(
            current_version, latest_version
        )
        if installed_on_pin:
            return make_plan(
                "up_to_date",
                latest_version=latest_version,
                latest_tag=latest_tag,
                reason="pinned_release_current",
                target_ref=latest_tag,
                target_version=latest_version,
            )
        if (
            target_source == "metadata"
            and latest_version
            and _current_newer_than(current_version, latest_version)
        ):
            return make_plan(
                "up_to_date",
                latest_version=latest_version,
                latest_tag=latest_tag,
                reason="target_drift_requires_force",
                target_ref=latest_tag,
                target_version=latest_version,
            )
    elif (
        selected_target.kind == "latest_release"
        and latest_version is not None
        and not force
    ):
        try:
            if Version(latest_version) <= Version(_public_version(current_version)):
                return make_plan(
                    "up_to_date",
                    latest_version=latest_version,
                    latest_tag=latest_tag,
                    target_ref=latest_tag,
                    target_version=latest_version,
                )
        except InvalidVersion:
            return make_plan(
                "unsupported_install_method",
                latest_version=latest_version,
                latest_tag=latest_tag,
                reason="could_not_parse_current_version",
            )
    elif (
        selected_target.kind == "custom_ref"
        and metadata.source_ref == latest_tag
        and not force
    ):
        return make_plan(
            "up_to_date",
            latest_version=latest_version,
            latest_tag=latest_tag,
            reason="custom_ref_current",
            target_ref=latest_tag,
            target_version=latest_version,
        )

    install_ref = (
        main_ref.remote_commit
        if selected_target.kind == "main" and main_ref is not None
        else latest_tag
    )
    command, cwd = _command_for_method(
        install_method,
        latest_tag=install_ref,
        repo=repo,
        platform_name=platform_name,
        source_root=source_root,
        target=selected_target,
    )
    if command is None:
        return make_plan(
            "unsupported_install_method",
            latest_version=latest_version,
            latest_tag=latest_tag,
            reason="unsupported_target_for_install_method",
            target_ref=latest_tag,
            target_version=latest_version,
        )
    plan_status = "dry_run" if dry_run else "update_available"
    target_commit = (
        main_ref.remote_commit if selected_target.kind == "main" and main_ref else None
    )
    current_commit = (
        main_ref.current_commit
        if selected_target.kind == "main" and main_ref and main_ref.current_commit
        else (
            _installed_main_commit(metadata) if selected_target.kind == "main" else None
        )
    )
    return make_plan(
        plan_status,
        latest_version=latest_version,
        latest_tag=latest_tag,
        command=command,
        reason="main_fallback_allowed"
        if used_main_fallback
        else (
            "main_commit_behind"
            if selected_target.kind == "main" and target_commit != current_commit
            else "update_available"
        ),
        cwd=str(cwd) if cwd else None,
        target_ref=latest_tag,
        target_version=latest_version,
        will_update_metadata=not dry_run,
        current_commit=current_commit,
        target_commit=target_commit,
    )


def apply_update(
    plan: UpdatePlan, *, runner: CommandRunner, timeout_seconds: int = 600
) -> CommandResult:
    """Run the plan command and return captured output."""
    if plan.command is None:
        _log.info(
            "Update skipped — nothing to apply",
            extra={"event": "update.apply_skipped", "context": {"status": plan.status}},
        )
        return CommandResult(0, "", "")
    if plan.install_method == "source":
        if plan.cwd is None:
            return CommandResult(1, "", "source checkout not found")
        dirty = runner.run(
            ["git", "status", "--porcelain"],
            timeout_seconds=timeout_seconds,
            cwd=plan.cwd,
        )
        if dirty.returncode != 0:
            return dirty
        if dirty.stdout.strip():
            return CommandResult(
                1,
                "",
                "source checkout has uncommitted changes (source_checkout_dirty)",
            )
        commands = plan.command if _is_command_sequence(plan.command) else []
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        for command in commands:
            executable = command[0]
            if shutil.which(executable) is None:
                return CommandResult(1, "", f"{executable} is not available on PATH")
            result = runner.run(command, timeout_seconds=timeout_seconds, cwd=plan.cwd)
            stdout_parts.append(result.stdout)
            stderr_parts.append(result.stderr)
            if result.returncode != 0:
                return CommandResult(
                    result.returncode, "".join(stdout_parts), "".join(stderr_parts)
                )
        return CommandResult(0, "".join(stdout_parts), "".join(stderr_parts))

    command = plan.command if _is_single_command(plan.command) else []
    executable = command[0]
    if shutil.which(executable) is None:
        return CommandResult(1, "", f"{executable} is not available on PATH")
    result = runner.run(command, timeout_seconds=timeout_seconds, cwd=plan.cwd)
    return result


def write_install_metadata_update(
    plan: UpdatePlan, *, platform_name: str | None = None
) -> Path | None:
    """Persist target tracking metadata after a successful mutating upgrade."""
    if not plan.will_update_metadata:
        return None
    payload = plan.metadata_update
    if payload is None:
        return None
    path = (
        Path(plan.metadata_path)
        if plan.metadata_path
        else _default_metadata_path(platform_name)
    )
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    existing: dict[str, object]
    try:
        loaded = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        existing = loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError):
        existing = {}
    merged = {**existing, **payload}
    if "installed_at" not in merged:
        merged["installed_at"] = _utc_now()
    _atomic_write_json(path, merged)
    return path


def metadata_update_payload(
    *,
    metadata: InstallMetadata,
    install_method: InstallMethod,
    target: TrackingTarget,
    resolved_ref: str | None,
    resolved_version: str | None,
    release_url: str | None,
    repo: str,
    resolved_commit: str | None = None,
) -> dict[str, object]:
    now = _utc_now()
    payload: dict[str, object] = {
        "metadata_version": 2,
        "install_method": install_method,
        "updated_at": now,
        "source_ref": resolved_commit
        if target.kind == "main" and resolved_commit
        else resolved_ref,
        "source_ref_kind": "release"
        if target.kind == "latest_release"
        else target.kind,
        "source_repo": repo,
        "tracking_target": _tracking_target_dict(_target_with_repo(target, repo)),
        "last_resolved": {
            "ref": resolved_ref,
            "version": resolved_version,
            "resolved_at": now,
        },
    }
    if resolved_commit is not None:
        last_resolved = payload["last_resolved"]
        if isinstance(last_resolved, dict):
            last_resolved["commit"] = resolved_commit
    if release_url is not None:
        last_resolved = payload["last_resolved"]
        if isinstance(last_resolved, dict):
            last_resolved["release_url"] = release_url
    if metadata.installed_at is not None:
        payload["installed_at"] = metadata.installed_at
    return payload


def plan_to_dict(plan: UpdatePlan) -> dict[str, object]:
    """Return a JSON-ready plan dict."""
    return {
        "status": plan.status,
        "current_version": plan.current_version,
        "latest_version": plan.latest_version,
        "latest_tag": plan.latest_tag,
        "install_method": plan.install_method,
        "command": plan.command,
        "reason": plan.reason,
        "metadata_path": plan.metadata_path,
        "cwd": plan.cwd,
        "target_kind": plan.target_kind,
        "target_selector": plan.target_selector,
        "target_ref": plan.target_ref,
        "target_version": plan.target_version,
        "target_source": plan.target_source,
        "will_update_metadata": plan.will_update_metadata,
        "metadata_update": plan.metadata_update,
        "current_commit": plan.current_commit,
        "target_commit": plan.target_commit,
    }


def find_source_checkout_root(start: Path) -> Path | None:
    """Return nearest parent containing pyproject and .git for Recollectium."""
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists() and (candidate / "pyproject.toml").exists():
            try:
                text = (candidate / "pyproject.toml").read_text(encoding="utf-8")
            except OSError:
                continue
            if 'name = "recollectium"' in text:
                return candidate
    return None


def _parse_tracking_target(
    raw: object, fallback_repo: object = None
) -> TrackingTarget | None:
    if not isinstance(raw, dict):
        return None
    kind = raw.get("kind")
    if kind not in _TARGET_KINDS:
        return None
    selector = raw.get("selector")
    repo = raw.get("repo") if isinstance(raw.get("repo"), str) else fallback_repo
    repo = (
        repo if isinstance(repo, str) and is_safe_github_repo(repo) else _DEFAULT_REPO
    )
    version = raw.get("version")
    ref = raw.get("ref")
    target = TrackingTarget(
        kind=kind,  # type: ignore[arg-type]
        selector=selector if isinstance(selector, str) else None,
        repo=repo,
        version=version if isinstance(version, str) else None,
        ref=ref if isinstance(ref, str) else None,
    )
    if target.kind == "latest_release":
        return target
    if target.kind == "main":
        return TrackingTarget(kind="main", selector="main", repo=repo, ref="main")
    if target.kind == "release":
        if target.ref and is_safe_ref(target.ref) and target.version:
            return target
        if target.selector:
            try:
                return _target_with_repo(
                    normalize_version_selector(target.selector), repo
                )
            except TargetSelectorError:
                return None
    if target.kind == "custom_ref" and target.ref and is_safe_ref(target.ref):
        return target
    return None


def _tracking_target_dict(target: TrackingTarget) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": target.kind,
        "selector": target.selector,
        "repo": target.repo,
    }
    if target.version is not None:
        payload["version"] = target.version
    if target.ref is not None:
        payload["ref"] = target.ref
    return payload


def _target_with_repo(target: TrackingTarget, repo: str) -> TrackingTarget:
    return TrackingTarget(
        kind=target.kind,
        selector=target.selector,
        repo=repo,
        version=target.version,
        ref=target.ref,
    )


def _version_from_tag(tag: str) -> str | None:
    normalized = tag[1:] if tag.startswith("v") else tag
    try:
        return str(Version(normalized))
    except InvalidVersion:
        return None


def _public_version(version: str) -> str:
    return str(Version(version).public)


def _versions_equal(current: str, expected: str | None) -> bool:
    if expected is None:
        return False
    try:
        return Version(_public_version(current)) == Version(expected)
    except InvalidVersion:
        return False


def _current_newer_than(current: str, expected: str) -> bool:
    try:
        return Version(_public_version(current)) > Version(expected)
    except InvalidVersion:
        return False


def _command_for_method(
    install_method: InstallMethod,
    *,
    latest_tag: str,
    repo: str,
    platform_name: str | None,
    source_root: Path | None,
    target: TrackingTarget | None = None,
) -> tuple[CommandSpec | None, Path | None]:
    target_kind = target.kind if target else "latest_release"
    target_version = target.version if target else _version_from_tag(latest_tag)
    if install_method == "pip":
        if target_kind in {"main", "custom_ref"}:
            return [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                _package_spec_for_target(target_kind, target_version, latest_tag, repo),
            ], None
        package = "recollectium"
        if target_kind == "release" and target_version is not None:
            package = f"recollectium=={target_version}"
        return [sys.executable, "-m", "pip", "install", "--upgrade", package], None
    if install_method == "pipx":
        if target_kind == "latest_release":
            return ["pipx", "upgrade", "recollectium"], None
        package = _package_spec_for_target(
            target_kind, target_version, latest_tag, repo
        )
        return ["pipx", "install", "--force", package], None
    if install_method == "uv_tool":
        if target_kind == "latest_release":
            return ["uv", "tool", "upgrade", "recollectium"], None
        package = _package_spec_for_target(
            target_kind, target_version, latest_tag, repo
        )
        return ["uv", "tool", "install", "--force", package], None
    if install_method == "source":
        root = source_root or find_source_checkout_root(Path(__file__).resolve())
        if target_kind == "main":
            return [
                ["git", "fetch", "origin", "main"],
                ["git", "checkout", latest_tag],
                ["uv", "sync", "--group", "dev"],
            ], root
        return [
            ["git", "fetch", "--tags", "origin"],
            ["git", "checkout", latest_tag],
            ["uv", "sync", "--group", "dev"],
        ], root
    if install_method == "bootstrap":
        target_env = _bootstrap_target_env(
            target or TrackingTarget("latest_release", "latest"), latest_tag
        )
        if (platform_name or platform.system()).lower().startswith("win"):
            script = (
                f"https://raw.githubusercontent.com/{repo}/{latest_tag}/install.ps1"
            )
            assignment = "; ".join(f"$env:{k}='{v}'" for k, v in target_env.items())
            return [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-c",
                f"{assignment}; irm {script} | iex",
            ], None
        script = f"https://raw.githubusercontent.com/{repo}/{latest_tag}/install.sh"
        assignment = " ".join(f"{k}={_shell_quote(v)}" for k, v in target_env.items())
        return ["sh", "-c", f"curl -LsSf {script} | {assignment} sh"], None
    return [], None


def _package_spec_for_target(
    target_kind: str, target_version: str | None, latest_tag: str, repo: str
) -> str:
    if target_kind == "release" and target_version is not None:
        return f"recollectium=={target_version}"
    return f"git+https://github.com/{repo}.git@{latest_tag}"


def _bootstrap_target_env(target: TrackingTarget, resolved_ref: str) -> dict[str, str]:
    if target.kind == "latest_release":
        return {
            "RECOLLECTIUM_INSTALL_VERSION": target.selector or "latest",
            "RECOLLECTIUM_INSTALL_RESOLVED_REF": resolved_ref,
            "RECOLLECTIUM_INSTALL_TRACKING": "latest_release",
        }
    if target.kind == "release":
        return {"RECOLLECTIUM_INSTALL_VERSION": target.selector or resolved_ref}
    if target.kind == "main":
        return {
            "RECOLLECTIUM_INSTALL_MAIN": "1",
            "RECOLLECTIUM_INSTALL_RESOLVED_REF": resolved_ref,
        }
    return {"RECOLLECTIUM_INSTALL_REF": resolved_ref}


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def is_safe_github_repo(repo: str) -> bool:
    """Return True when repo is a safe GitHub OWNER/REPO path."""
    return bool(_GITHUB_REPO_PATTERN.fullmatch(repo))


def is_safe_ref(ref: str) -> bool:
    """Return True when a release tag/source ref is safe for raw GitHub URLs."""
    return (
        bool(_SAFE_REF_PATTERN.fullmatch(ref))
        and ".." not in ref
        and "@{" not in ref
        and "://" not in ref
        and not ref.startswith("/")
        and not ref.endswith((".", "/"))
    )


def is_commit_sha(value: str) -> bool:
    """Return True when value is a full Git commit SHA."""
    return bool(_COMMIT_SHA_PATTERN.fullmatch(value))


def _parse_commit_sha(output: str) -> str | None:
    first = output.strip().split()[0] if output.strip() else ""
    return first.lower() if is_commit_sha(first) else None


def _installed_main_commit(metadata: InstallMetadata) -> str | None:
    for value in (
        metadata.last_resolved_commit,
        metadata.source_ref,
        metadata.last_resolved_ref,
    ):
        if value is not None and is_commit_sha(value):
            return value.lower()
    return None


def _default_metadata_path(platform_name: str | None = None) -> Path:
    if (platform_name or platform.system()).lower().startswith("win"):
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "recollectium" / "install.json"
    return Path(user_state_dir("recollectium")) / "install.json"


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, path)
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_single_command(command: CommandSpec) -> TypeGuard[list[str]]:
    return bool(command) and isinstance(command[0], str)


def _is_command_sequence(command: CommandSpec) -> TypeGuard[list[list[str]]]:
    return bool(command) and isinstance(command[0], list)

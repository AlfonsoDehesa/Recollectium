"""Bootstrap shell completion lifecycle script checks."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_unix_bootstrap_unknown_shell_falls_back_to_bash_completion() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert 'shell="bash"' in script
    assert 'rc="${HOME}/.bashrc"' in script
    assert 'recollectium completion --install "$shell" --yes' in script
    assert "managed_completion_edits" in script


def test_unix_bootstrap_adds_path_to_zsh_startup_files() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert 'case ":${PATH}:"' in script
    assert '*":${TOOL_BIN_DIR}:"*) return ;;' in script
    assert 'detected_shell="${SHELL##*/}"' in script
    assert 'if [ "$detected_shell" = "zsh" ]; then' in script
    assert 'zdotdir="${ZDOTDIR:-$HOME}"' in script
    assert 'ensure_path_file "${zdotdir}/.zprofile"' in script
    assert 'ensure_path_file "${zdotdir}/.zshrc"' in script


def test_unix_bootstrap_records_managed_path_edit_paths() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert 'MANAGED_PATH_EDITS=""' in script
    assert "append_managed_path_edit()" in script
    assert 'MANAGED_PATH_EDITS="${MANAGED_PATH_EDITS}${path}\n"' in script
    assert "while IFS= read -r path_edit; do" in script


def test_unix_bootstrap_uses_guarded_idempotent_path_block() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert 'start_marker="# >>> recollectium path >>>"' in script
    assert 'end_marker="# <<< recollectium path <<<"' in script
    assert 'grep -F "$start_marker" "$profile"' in script
    assert 'grep -F "$line" "$profile"' in script
    assert "printf '\\n%s\\n%s\\n%s\\n'" in script


def test_unix_bootstrap_resolves_tracking_metadata_in_current_shell() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert "ref=$(resolve_ref)" not in script
    assert 'resolve_ref\nref="$RESOLVED_REF"' in script
    assert 'RESOLVED_REF="main"' in script
    assert 'RESOLVED_REF="$ref"' in script


def test_windows_bootstrap_installs_powershell_current_user_current_host_completion() -> (
    None
):
    script = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "$PROFILE.CurrentUserCurrentHost" in script
    assert "RECOLLECTIUM_POWERSHELL_PROFILE" in script
    assert "recollectium completion --install powershell --yes" in script
    assert "managed_completion_edits" in script

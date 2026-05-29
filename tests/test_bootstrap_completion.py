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


def test_windows_bootstrap_installs_powershell_current_user_current_host_completion() -> (
    None
):
    script = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "$PROFILE.CurrentUserCurrentHost" in script
    assert "RECOLLECTIUM_POWERSHELL_PROFILE" in script
    assert "recollectium completion --install powershell --yes" in script
    assert "managed_completion_edits" in script

"""Bootstrap shell completion lifecycle script checks."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from platformdirs.macos import MacOS


ROOT = Path(__file__).resolve().parents[1]


def _unix_bootstrap_helpers() -> str:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")
    return script.split('\nmain "$@"\n', maxsplit=1)[0]


def test_unix_bootstrap_unknown_shell_falls_back_to_bash_completion() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert 'shell="bash"' in script
    assert 'rc="${HOME}/.bashrc"' in script
    assert 'recollectium completion --install "$shell" --yes' in script
    assert "managed_completion_edits" in script


def test_unix_bootstrap_adds_path_to_zsh_startup_files() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert 'case ":${ORIGINAL_PATH}:"' in script
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


def test_unix_bootstrap_repairs_empty_managed_path_block(tmp_path: Path) -> None:
    helpers = _unix_bootstrap_helpers()
    tool_bin = tmp_path / "uv-tools"
    profile = tmp_path / ".zprofile"
    tool_bin.mkdir()
    profile.write_text(
        "before\n# >>> recollectium path >>>\n# <<< recollectium path <<<\nafter\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            "sh",
            "-c",
            f'{helpers}\nTOOL_BIN_DIR="$1"\nensure_path_file "$2"\nensure_path_file "$2"',
            "sh",
            str(tool_bin),
            str(profile),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    expected_line = f'export PATH="{tool_bin}:$PATH"'
    content = profile.read_text(encoding="utf-8")
    assert content == (
        "before\n"
        "# >>> recollectium path >>>\n"
        f"{expected_line}\n"
        "# <<< recollectium path <<<\n"
        "after\n"
    )
    assert content.count(expected_line) == 1
    assert content.count("# >>> recollectium path >>>") == 1


def test_unix_bootstrap_does_not_duplicate_legacy_path_line(tmp_path: Path) -> None:
    helpers = _unix_bootstrap_helpers()
    tool_bin = tmp_path / "uv-tools"
    profile = tmp_path / ".profile"
    tool_bin.mkdir()
    expected_line = f'export PATH="{tool_bin}:$PATH"'
    profile.write_text(f"before\n{expected_line}\nafter\n", encoding="utf-8")

    subprocess.run(
        [
            "sh",
            "-c",
            f'{helpers}\nTOOL_BIN_DIR="$1"\nensure_path_file "$2"',
            "sh",
            str(tool_bin),
            str(profile),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    content = profile.read_text(encoding="utf-8")
    assert content == f"before\n{expected_line}\nafter\n"
    assert content.count(expected_line) == 1
    assert "# >>> recollectium path >>>" not in content


def test_unix_bootstrap_removes_legacy_path_line_when_repairing_block(
    tmp_path: Path,
) -> None:
    helpers = _unix_bootstrap_helpers()
    tool_bin = tmp_path / "uv-tools"
    profile = tmp_path / ".zshrc"
    tool_bin.mkdir()
    expected_line = f'export PATH="{tool_bin}:$PATH"'
    profile.write_text(
        f"before\n{expected_line}\n"
        "# >>> recollectium path >>>\n"
        "# <<< recollectium path <<<\n"
        "after\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            "sh",
            "-c",
            f'{helpers}\nTOOL_BIN_DIR="$1"\nensure_path_file "$2"',
            "sh",
            str(tool_bin),
            str(profile),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    content = profile.read_text(encoding="utf-8")
    assert content == (
        "before\n"
        "# >>> recollectium path >>>\n"
        f"{expected_line}\n"
        "# <<< recollectium path <<<\n"
        "after\n"
    )
    assert content.count(expected_line) == 1


def test_bootstrap_installers_run_embedding_maintenance_strictly() -> None:
    unix_script = (ROOT / "install.sh").read_text(encoding="utf-8")
    windows_script = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "recollectium embedding-maintenance" in unix_script
    assert "recollectium init || true" not in unix_script
    assert "recollectium embedding-maintenance" in windows_script
    assert "failed to install Recollectium package" in windows_script
    assert (
        "embedding maintenance failed; retry with: recollectium embedding-maintenance"
        in windows_script
    )


def test_bootstrap_installers_have_main_phase_orchestration() -> None:
    unix_script = (ROOT / "install.sh").read_text(encoding="utf-8")
    windows_script = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "main()" in unix_script
    assert "phase_install_package" in unix_script
    assert "phase_run_maintenance" in unix_script
    assert "phase_configure_path_and_completion" in unix_script
    assert 'main "$@"' in unix_script
    assert "function Main" in windows_script
    assert "Install-PackagePhase" in windows_script
    assert "Invoke-MaintenancePhase" in windows_script
    assert "Configure-PathAndCompletionPhase" in windows_script
    assert "Main\n" in windows_script


def test_bootstrap_installers_support_quiet_progress_and_verbose_opt_in() -> None:
    unix_script = (ROOT / "install.sh").read_text(encoding="utf-8")
    windows_script = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "RECOLLECTIUM_INSTALL_VERBOSE" in unix_script
    assert "run_with_progress" in unix_script
    assert "Captured command output:" in unix_script
    assert "Installing Recollectium from ${ref}..." in unix_script
    assert (
        "Maintaining embeddings (config, database, model, stale memories)..."
        in unix_script
    )
    assert "RECOLLECTIUM_INSTALL_VERBOSE" in windows_script
    assert "Invoke-NativeInstallerPhase" in windows_script
    assert "Captured command output:" in windows_script
    assert "Installing Recollectium from $script:Ref..." in windows_script
    assert (
        "Maintaining embeddings (config, database, model, stale memories)..."
        in windows_script
    )


def test_unix_bootstrap_resolves_tracking_metadata_in_current_shell() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert "ref=$(resolve_ref)" not in script
    assert "resolve_ref" in script
    assert 'ref="$RESOLVED_REF"' in script
    assert "RESOLVED_REF=$(resolve_main_commit)" in script
    assert 'RESOLVED_REF="$ref"' in script


def test_unix_bootstrap_resolved_main_ref_installs_commit_but_tracks_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helpers = _unix_bootstrap_helpers()
    home = tmp_path / "home"
    state = tmp_path / "state"
    home.mkdir()
    state.mkdir()
    commit = "0123456789abcdef0123456789abcdef01234567"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_STATE_HOME", str(state))

    result = subprocess.run(
        [
            "sh",
            "-c",
            f'{helpers}\nresolve_ref\nref="$RESOLVED_REF"\nrecord_install_metadata\nprintf \'%s\' "$metadata_path"',
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(home),
            "XDG_STATE_HOME": str(state),
            "PATH": "/usr/bin:/bin",
            "RECOLLECTIUM_INSTALL_MAIN": "1",
            "RECOLLECTIUM_INSTALL_RESOLVED_REF": commit,
        },
    )

    metadata = json.loads(Path(result.stdout).read_text(encoding="utf-8"))
    assert metadata["source_ref"] == commit
    assert metadata["source_ref_kind"] == "main"
    assert metadata["tracking_target"] == {
        "kind": "main",
        "selector": "main",
        "repo": "AlfonsoDehesa/recollectium",
        "ref": "main",
    }
    assert metadata["last_resolved"]["ref"] == "main"
    assert metadata["last_resolved"]["commit"] == commit


def test_unix_bootstrap_plain_main_resolves_commit_and_records_main_ref(
    tmp_path: Path,
) -> None:
    helpers = _unix_bootstrap_helpers()
    home = tmp_path / "home"
    state = tmp_path / "state"
    fake_bin = tmp_path / "bin"
    home.mkdir()
    state.mkdir()
    fake_bin.mkdir()
    commit = "abcdef0123456789abcdef0123456789abcdef01"
    git = fake_bin / "git"
    git.write_text(
        f"#!/bin/sh\nprintf '%s\\trefs/heads/main\\n' '{commit}'\n",
        encoding="utf-8",
    )
    git.chmod(0o755)

    result = subprocess.run(
        [
            "sh",
            "-c",
            f'{helpers}\nresolve_ref\nref="$RESOLVED_REF"\nrecord_install_metadata\nprintf \'%s\' "$metadata_path"',
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(home),
            "XDG_STATE_HOME": str(state),
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "RECOLLECTIUM_INSTALL_MAIN": "1",
        },
    )

    metadata = json.loads(Path(result.stdout).read_text(encoding="utf-8"))
    assert metadata["source_ref"] == commit
    assert metadata["source_ref_kind"] == "main"
    assert metadata["tracking_target"]["ref"] == "main"
    assert metadata["last_resolved"]["ref"] == "main"
    assert metadata["last_resolved"]["commit"] == commit


def test_unix_bootstrap_json_escape_does_not_corrupt_plain_f() -> None:
    bootstrap_helpers = _unix_bootstrap_helpers().split(
        "\ndetect_uv_archive() {", maxsplit=1
    )[0]

    result = subprocess.run(
        [
            "sh",
            "-c",
            f'{bootstrap_helpers}\njson_escape "fix/feature\\"slash\\\\path"',
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == 'fix/feature\\"slash\\\\path'


def test_unix_bootstrap_prints_only_durable_path_message_when_path_was_missing(
    tmp_path: Path,
) -> None:
    helpers = _unix_bootstrap_helpers()
    home = tmp_path / "home"
    tool_bin = tmp_path / "uv-tools"
    home.mkdir()
    tool_bin.mkdir()

    result = subprocess.run(
        [
            "sh",
            "-c",
            f'{helpers}\nTOOL_BIN_DIR="$1"\nensure_path_hint',
            "sh",
            str(tool_bin),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(home),
            "PATH": "/usr/bin:/bin",
            "SHELL": "/bin/bash",
        },
    )

    assert f"Added {tool_bin} to {home / '.profile'}" in result.stdout
    assert "Restart your terminal session" not in result.stdout
    assert "To use recollectium in this shell now, run:" not in result.stdout
    assert "Then verify with: recollectium --version" not in result.stdout


def test_unix_bootstrap_uses_original_path_for_durable_path_hint(
    tmp_path: Path,
) -> None:
    helpers = _unix_bootstrap_helpers()
    home = tmp_path / "home"
    tool_bin = tmp_path / "uv-tools"
    home.mkdir()
    tool_bin.mkdir()

    result = subprocess.run(
        [
            "sh",
            "-c",
            f'{helpers}\nTOOL_BIN_DIR="$1"\nORIGINAL_PATH="/usr/bin:/bin"\nPATH="$1:$ORIGINAL_PATH"\nensure_path_hint',
            "sh",
            str(tool_bin),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(home),
            "PATH": "/usr/bin:/bin",
            "SHELL": "/bin/bash",
        },
    )

    assert f"Added {tool_bin} to {home / '.profile'}" in result.stdout
    assert f'export PATH="{tool_bin}:$PATH"' not in result.stdout


def test_unix_bootstrap_prints_final_guidance_without_source_guidance() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert "print_final_guidance()" in script
    assert "Open a new terminal window before using recollectium" in script
    assert "current_terminal_path_command()" in script
    assert 'export PATH="%s:$PATH"' in script
    assert "__recollectium_path_check_$$__" in script
    assert "command -v recollectium" in script
    assert "seen_sentinel=0" in script
    assert 'source "${COMPLETION_RC}"' not in script
    assert "source ${COMPLETION_RC}" not in script


def test_unix_final_guidance_current_path_resolves_installed_executable(
    tmp_path: Path,
) -> None:
    helpers = _unix_bootstrap_helpers()
    tool_bin = tmp_path / "uv-tools"
    tool_bin.mkdir()
    recollectium = tool_bin / "recollectium"
    recollectium.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    recollectium.chmod(0o755)

    result = subprocess.run(
        [
            "sh",
            "-c",
            f'{helpers}\nTOOL_BIN_DIR="$1"\nORIGINAL_PATH="$1:/usr/bin:/bin"\nprint_final_guidance',
            "sh",
            str(tool_bin),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(tmp_path / "home"),
            "PATH": f"{tool_bin}:/usr/bin:/bin",
            "SHELL": "/bin/bash",
        },
    )

    assert (
        result.stdout
        == "Recollectium installed.\nVerify with: recollectium --version\n"
    )
    assert "Restart your terminal session" not in result.stdout
    assert "export PATH" not in result.stdout
    assert "source" not in result.stdout


def test_unix_final_guidance_current_missing_but_future_shell_resolves(
    tmp_path: Path,
) -> None:
    helpers = _unix_bootstrap_helpers()
    tool_bin = tmp_path / "uv-tools"
    fake_bin = tmp_path / "fake-bin"
    tool_bin.mkdir()
    fake_bin.mkdir()
    recollectium = tool_bin / "recollectium"
    recollectium.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    recollectium.chmod(0o755)
    zsh = fake_bin / "zsh"
    zsh.write_text(
        "#!/bin/sh\nprintf '%s\\n' 'startup noise'\nPATH=\"$FUTURE_TOOL_BIN:$PATH\" eval \"$2\"\n",
        encoding="utf-8",
    )
    zsh.chmod(0o755)

    result = subprocess.run(
        [
            "sh",
            "-c",
            f'{helpers}\nTOOL_BIN_DIR="$1"\nORIGINAL_PATH="$2:/usr/bin:/bin"\nprint_final_guidance',
            "sh",
            str(tool_bin),
            str(fake_bin),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(tmp_path / "home"),
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "SHELL": "/bin/bash",
            "FUTURE_TOOL_BIN": str(tool_bin),
        },
    )

    assert "Recollectium installed." in result.stdout
    assert "Open a new terminal window before using recollectium" in result.stdout
    assert f'export PATH="{tool_bin}:$PATH"' in result.stdout
    assert "Then verify with: recollectium --version" in result.stdout
    assert "source" not in result.stdout


def test_unix_final_guidance_current_and_future_path_verification_fail(
    tmp_path: Path,
) -> None:
    helpers = _unix_bootstrap_helpers()
    tool_bin = tmp_path / "uv-tools"
    profile = tmp_path / "home" / ".profile"
    tool_bin.mkdir()

    result = subprocess.run(
        [
            "sh",
            "-c",
            (
                f'{helpers}\nTOOL_BIN_DIR="$1"\nORIGINAL_PATH="/usr/bin:/bin"\n'
                'MANAGED_PATH_EDITS="$2\n"\nprint_final_guidance'
            ),
            "sh",
            str(tool_bin),
            str(profile),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(tmp_path / "home"),
            "PATH": "/usr/bin:/bin",
            "SHELL": "/bin/bash",
        },
    )

    assert (
        "PATH files were updated, but PATH setup could not be verified" in result.stdout
    )
    assert f'export PATH="{tool_bin}:$PATH"' in result.stdout
    assert f"Managed PATH files updated: {profile}" in result.stdout
    assert "Add Recollectium to your shell startup file" not in result.stdout
    assert (
        "Restart your terminal, or run this command in the current terminal:"
        in result.stdout
    )
    assert "Then verify with: recollectium --version" in result.stdout


def test_unix_final_guidance_without_managed_edits_tells_user_to_edit_startup_file(
    tmp_path: Path,
) -> None:
    helpers = _unix_bootstrap_helpers()
    tool_bin = tmp_path / "uv-tools"
    tool_bin.mkdir()

    result = subprocess.run(
        [
            "sh",
            "-c",
            f'{helpers}\nTOOL_BIN_DIR="$1"\nORIGINAL_PATH="/usr/bin:/bin"\nprint_final_guidance',
            "sh",
            str(tool_bin),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(tmp_path / "home"),
            "PATH": "/usr/bin:/bin",
            "SHELL": "/bin/bash",
        },
    )

    assert (
        "Recollectium installed, but PATH setup could not be verified." in result.stdout
    )
    assert "Add Recollectium to your shell startup file:" in result.stdout
    assert f'export PATH="{tool_bin}:$PATH"' in result.stdout
    assert "Managed PATH files updated" not in result.stdout
    assert (
        "Then restart your terminal, or run the command above in the current terminal."
        in result.stdout
    )
    assert "Then verify with: recollectium --version" in result.stdout


def test_unix_final_guidance_zsh_path_edit_does_not_force_restart_when_current_resolves(
    tmp_path: Path,
) -> None:
    helpers = _unix_bootstrap_helpers()
    tool_bin = tmp_path / "uv-tools"
    profile = tmp_path / "home" / ".zshrc"
    tool_bin.mkdir(parents=True)
    recollectium = tool_bin / "recollectium"
    recollectium.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    recollectium.chmod(0o755)

    result = subprocess.run(
        [
            "sh",
            "-c",
            (
                f'{helpers}\nTOOL_BIN_DIR="$1"\nORIGINAL_PATH="$1:/usr/bin:/bin"\n'
                'MANAGED_PATH_EDITS="$2\n"\nprint_final_guidance'
            ),
            "sh",
            str(tool_bin),
            str(profile),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(tmp_path / "home"),
            "PATH": f"{tool_bin}:/usr/bin:/bin",
            "SHELL": "/bin/zsh",
        },
    )

    assert (
        result.stdout
        == "Recollectium installed.\nVerify with: recollectium --version\n"
    )
    assert "Restart your terminal session" not in result.stdout
    assert "Managed PATH files updated" not in result.stdout


def test_unix_final_guidance_fish_current_terminal_path_command(
    tmp_path: Path,
) -> None:
    helpers = _unix_bootstrap_helpers()
    tool_bin = tmp_path / "uv tools"
    tool_bin.mkdir()

    result = subprocess.run(
        [
            "sh",
            "-c",
            f'{helpers}\nTOOL_BIN_DIR="$1"\nORIGINAL_PATH="/usr/bin:/bin"\nprint_final_guidance',
            "sh",
            str(tool_bin),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(tmp_path / "home"),
            "PATH": "/usr/bin:/bin",
            "SHELL": "/usr/bin/fish",
        },
    )

    assert f'set -gx PATH "{tool_bin}" $PATH' in result.stdout
    assert f'export PATH="{tool_bin}:$PATH"' not in result.stdout
    assert "source" not in result.stdout


def test_unix_final_guidance_no_color_disables_ansi(tmp_path: Path) -> None:
    helpers = _unix_bootstrap_helpers()
    tool_bin = tmp_path / "uv-tools"
    tool_bin.mkdir()

    result = subprocess.run(
        [
            "sh",
            "-c",
            (
                f"{helpers}\nrecollectium_stdout_is_tty() {{ return 0; }}\n"
                'TOOL_BIN_DIR="$1"\nORIGINAL_PATH="/usr/bin:/bin"\nprint_final_guidance'
            ),
            "sh",
            str(tool_bin),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(tmp_path / "home"),
            "PATH": "/usr/bin:/bin",
            "SHELL": "/bin/bash",
            "NO_COLOR": "1",
        },
    )

    assert "\033[" not in result.stdout


def test_unix_final_guidance_color_supported_path_includes_ansi(
    tmp_path: Path,
) -> None:
    helpers = _unix_bootstrap_helpers()
    tool_bin = tmp_path / "uv-tools"
    fake_bin = tmp_path / "fake-bin"
    tool_bin.mkdir()
    fake_bin.mkdir()
    recollectium = tool_bin / "recollectium"
    recollectium.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    recollectium.chmod(0o755)
    zsh = fake_bin / "zsh"
    zsh.write_text(
        "#!/bin/sh\nprintf '%s\\n' 'startup noise'\nPATH=\"$FUTURE_TOOL_BIN:$PATH\" eval \"$2\"\n",
        encoding="utf-8",
    )
    zsh.chmod(0o755)

    result = subprocess.run(
        [
            "sh",
            "-c",
            (
                f"{helpers}\nrecollectium_stdout_is_tty() {{ return 0; }}\n"
                'TOOL_BIN_DIR="$1"\nORIGINAL_PATH="$2:/usr/bin:/bin"\nprint_final_guidance'
            ),
            "sh",
            str(tool_bin),
            str(fake_bin),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(tmp_path / "home"),
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "SHELL": "/bin/bash",
            "FUTURE_TOOL_BIN": str(tool_bin),
        },
    )

    assert "\033[32m" in result.stdout
    assert "\033[33m" in result.stdout


def test_unix_bootstrap_resolves_uv_tool_bin_before_tool_install() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    main_block = script.split("phase_install_package() {", maxsplit=1)[1]
    install_index = main_block.index("run_with_progress")
    resolve_index = main_block.index("resolve_tool_bin_dir")
    assert resolve_index < install_index
    assert 'PATH="${TOOL_BIN_DIR}:${ORIGINAL_PATH}"' in main_block
    assert "verify_installed_tool" in main_block


def test_unix_bootstrap_keeps_concise_path_success_when_path_already_present(
    tmp_path: Path,
) -> None:
    helpers = _unix_bootstrap_helpers()
    tool_bin = tmp_path / "uv-tools"
    tool_bin.mkdir()

    result = subprocess.run(
        [
            "sh",
            "-c",
            f'{helpers}\nTOOL_BIN_DIR="$1"\nensure_path_hint\nprintf done',
            "sh",
            str(tool_bin),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(tmp_path / "home"),
            "PATH": f"/usr/bin:{tool_bin}:/bin",
            "SHELL": "/bin/bash",
        },
    )

    assert result.stdout == "done"


def test_unix_bootstrap_records_metadata_in_macos_platformdirs_state_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helpers = _unix_bootstrap_helpers()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    expected_state_dir = Path(MacOS("recollectium").user_state_dir)

    result = subprocess.run(
        [
            "sh",
            "-c",
            "uname() { printf 'Darwin\\n'; }\n"
            f'{helpers}\nref="main"\nTRACKING_KIND="main"\n'
            'TRACKING_SELECTOR="main"\nTRACKING_VERSION=""\n'
            'record_install_metadata\nprintf "%s" "$metadata_path"',
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(home),
            "PATH": "/usr/bin:/bin",
        },
    )

    assert Path(result.stdout) == expected_state_dir / "install.json"
    assert (
        json.loads(Path(result.stdout).read_text(encoding="utf-8"))["install_method"]
        == "bootstrap"
    )


def test_unix_bootstrap_records_metadata_in_macos_xdg_state_home(
    tmp_path: Path,
) -> None:
    helpers = _unix_bootstrap_helpers()
    home = tmp_path / "home"
    state = tmp_path / "state"
    home.mkdir()

    result = subprocess.run(
        [
            "sh",
            "-c",
            "uname() { printf 'Darwin\\n'; }\n"
            f'{helpers}\nref="main"\nTRACKING_KIND="main"\n'
            'TRACKING_SELECTOR="main"\nTRACKING_VERSION=""\n'
            'record_install_metadata\nprintf "%s" "$metadata_path"',
        ],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(home),
            "PATH": "/usr/bin:/bin",
            "XDG_STATE_HOME": str(state),
        },
    )

    assert Path(result.stdout) == state / "recollectium" / "install.json"
    assert (
        json.loads(Path(result.stdout).read_text(encoding="utf-8"))["install_method"]
        == "bootstrap"
    )


def test_unix_bootstrap_records_selector_tracking_targets(tmp_path: Path) -> None:
    helpers = _unix_bootstrap_helpers()
    cases = [
        (
            {
                "RECOLLECTIUM_INSTALL_MAIN": "1",
                "RECOLLECTIUM_INSTALL_RESOLVED_REF": "0123456789abcdef0123456789abcdef01234567",
            },
            "main",
            "main",
        ),
        ({"RECOLLECTIUM_INSTALL_VERSION": "1.2.3"}, "release", "v1.2.3"),
        (
            {
                "RECOLLECTIUM_INSTALL_VERSION": "latest",
                "RECOLLECTIUM_INSTALL_RESOLVED_REF": "v2.0.0",
            },
            "latest_release",
            "latest",
        ),
        ({"RECOLLECTIUM_INSTALL_REF": "v1.2.3"}, "release", "v1.2.3"),
        ({"RECOLLECTIUM_INSTALL_REF": "1.2.3"}, "release", "1.2.3"),
        ({"RECOLLECTIUM_INSTALL_REF": "feature/test"}, "custom_ref", "feature/test"),
    ]

    for index, (selector_env, expected_kind, expected_selector) in enumerate(cases):
        home = tmp_path / f"home-{index}"
        state = tmp_path / f"state-{index}"
        home.mkdir()
        result = subprocess.run(
            [
                "sh",
                "-c",
                f'{helpers}\nresolve_ref\nref="$RESOLVED_REF"\nrecord_install_metadata\nprintf "%s" "$metadata_path"',
            ],
            check=True,
            capture_output=True,
            text=True,
            env={
                "HOME": str(home),
                "PATH": "/usr/bin:/bin",
                "XDG_STATE_HOME": str(state),
                **selector_env,
            },
        )
        metadata = json.loads(Path(result.stdout).read_text(encoding="utf-8"))

        assert metadata["tracking_target"]["kind"] == expected_kind
        assert metadata["tracking_target"]["selector"] == expected_selector


def test_windows_bootstrap_resolved_main_ref_installs_commit_but_tracks_main() -> None:
    script = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert ("$ref = $env:RECOLLECTIUM_INSTALL_RESOLVED_REF") in script
    assert "$ref = Get-MainCommit" in script
    assert "if (Test-CommitSha $ref) { $script:ResolvedCommit = $ref }" in script
    assert 'elseif ($script:TrackingKind -eq "main") {' in script
    assert "$trackingTarget.ref = $script:TrackingSelector" in script
    assert 'ref = $(if ($script:TrackingKind -eq "main")' in script
    assert (
        "if ($script:ResolvedCommit) { $resolved.commit = $script:ResolvedCommit }"
        in script
    )


def test_windows_bootstrap_installs_powershell_current_user_current_host_completion() -> (
    None
):
    script = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "$PROFILE.CurrentUserCurrentHost" in script
    assert "RECOLLECTIUM_POWERSHELL_PROFILE" in script
    assert '"recollectium", "completion", "--install", "powershell", "--yes"' in script
    assert "managed_completion_edits" in script


def test_windows_final_guidance_current_session_resolves_installed_recollectium() -> (
    None
):
    script = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "function Test-CurrentRecollectiumPath" in script
    assert "Get-Command recollectium -ErrorAction SilentlyContinue" in script
    assert "Recollectium installed." in script
    assert "Verify with: recollectium --version" in script


def test_windows_final_guidance_future_path_resolves_with_restart_guidance() -> None:
    script = (ROOT / "install.ps1").read_text(encoding="utf-8")
    future_branch = script.split("if (Test-FutureRecollectiumPath)", maxsplit=1)[
        1
    ].split("if (Test-UserPathContainsToolBin)", maxsplit=1)[0]

    assert "function Test-FutureRecollectiumPath" in script
    assert "function Test-UserPathContainsToolBin" in script
    assert (
        "(Test-UserPathContainsToolBin) -or (Test-FutureRecollectiumPath)" not in script
    )
    assert "Open a new terminal window before using recollectium" in future_branch
    assert "Test-UserPathContainsToolBin" not in future_branch
    assert "$tempPathCommand" in future_branch
    assert '$env:Path = "{0};$env:Path"' in script
    assert "Then verify with: recollectium --version" in future_branch


def test_windows_final_guidance_user_path_only_uses_verification_failed_branch() -> (
    None
):
    script = (ROOT / "install.ps1").read_text(encoding="utf-8")
    user_path_branch = script.split("if (Test-UserPathContainsToolBin)", maxsplit=1)[
        1
    ].split(
        'Write-Guidance "Recollectium installed, but PATH setup could not be verified."',
        maxsplit=1,
    )[0]

    assert "PATH setup could not be verified for a new terminal" in user_path_branch
    assert "Your User Path already includes this directory:" in user_path_branch
    assert (
        "Open a new terminal window before using recollectium" not in user_path_branch
    )
    assert (
        "Restart your terminal, or run this command in the current terminal:"
        in user_path_branch
    )


def test_windows_final_guidance_path_verification_fails_with_add_to_path_guidance() -> (
    None
):
    script = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "Recollectium installed, but PATH setup could not be verified." in script
    assert "Add this directory to your User Path:" in script
    assert "Then verify with: recollectium --version" in script


def test_windows_final_guidance_no_color_disables_write_host_foreground_color() -> None:
    script = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "function Write-Guidance" in script
    assert "$env:NO_COLOR" in script
    assert "Write-Host $Message" in script
    assert "-ForegroundColor $Color" in script


def test_windows_final_guidance_color_supported_path_uses_write_host_color() -> None:
    script = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert 'Write-Guidance "Recollectium installed." Green' in script
    assert (
        'Write-Guidance "Recollectium installed, but PATH setup could not be verified." Yellow'
        in script
    )
    assert "Write-Guidance" in script

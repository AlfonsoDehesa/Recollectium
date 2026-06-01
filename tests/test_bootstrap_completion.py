"""Bootstrap shell completion lifecycle script checks."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _unix_bootstrap_helpers() -> str:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")
    return script.split("\ninstall_uv\n", maxsplit=1)[0]


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


def test_unix_bootstrap_resolves_tracking_metadata_in_current_shell() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert "ref=$(resolve_ref)" not in script
    assert 'resolve_ref\nref="$RESOLVED_REF"' in script
    assert 'RESOLVED_REF="main"' in script
    assert 'RESOLVED_REF="$ref"' in script


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


def test_unix_bootstrap_prints_current_shell_path_command_when_path_was_missing(
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

    assert f'export PATH="{tool_bin}:$PATH"' in result.stdout
    assert f"Added {tool_bin} to {home / '.profile'}" in result.stdout
    assert "To use recollectium in this shell now, run:" in result.stdout
    assert "Then verify with: recollectium --version" in result.stdout


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
    assert f'export PATH="{tool_bin}:$PATH"' in result.stdout


def test_unix_bootstrap_prints_final_restart_or_current_terminal_guidance() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert "print_final_guidance()" in script
    assert "Restart your terminal session" in script
    assert r"export PATH=\"${TOOL_BIN_DIR}:\$PATH\"" in script
    assert "source ${COMPLETION_RC}" in script


def test_unix_bootstrap_resolves_uv_tool_bin_before_tool_install() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    main_block = script.split(
        'package="git+https://github.com/${REPO}.git@${ref}"', maxsplit=1
    )[1]
    install_index = main_block.index('"$UV_BIN" tool install')
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


def test_unix_bootstrap_records_selector_tracking_targets(tmp_path: Path) -> None:
    helpers = _unix_bootstrap_helpers()
    cases = [
        ({"RECOLLECTIUM_INSTALL_MAIN": "1"}, "main", "main"),
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


def test_windows_bootstrap_installs_powershell_current_user_current_host_completion() -> (
    None
):
    script = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "$PROFILE.CurrentUserCurrentHost" in script
    assert "RECOLLECTIUM_POWERSHELL_PROFILE" in script
    assert "recollectium completion --install powershell --yes" in script
    assert "managed_completion_edits" in script

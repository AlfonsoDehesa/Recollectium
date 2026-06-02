#!/bin/sh
set -eu

REPO="AlfonsoDehesa/recollectium"
INSTALL_DIR="${HOME}/.local/bin"
UV_BIN="${INSTALL_DIR}/uv"
TOOL_BIN_DIR=""
ORIGINAL_PATH="${PATH:-}"
MANAGED_PATH_EDITS=""
COMPLETION_RC=""
COMPLETION_SHELL=""

info() {
  printf '%s\n' "$1"
}

fail() {
  printf 'error: %s\n' "$1" >&2
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

detect_uv_archive() {
  os=$(uname -s)
  arch=$(uname -m)

  case "$os:$arch" in
    Linux:x86_64|Linux:amd64) printf 'uv-x86_64-unknown-linux-gnu.tar.gz' ;;
    Linux:aarch64|Linux:arm64) printf 'uv-aarch64-unknown-linux-gnu.tar.gz' ;;
    Darwin:x86_64|Darwin:amd64) printf 'uv-x86_64-apple-darwin.tar.gz' ;;
    Darwin:arm64|Darwin:aarch64) printf 'uv-aarch64-apple-darwin.tar.gz' ;;
    *) fail "unsupported platform: ${os} ${arch}" ;;
  esac
}

install_uv() {
  if command_exists uv; then
    UV_BIN=$(command -v uv)
    info "uv already installed: ${UV_BIN}"
    return
  fi

  archive=$(detect_uv_archive)
  url="https://github.com/astral-sh/uv/releases/latest/download/${archive}"
  tmpdir=$(mktemp -d)
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM

  mkdir -p "$INSTALL_DIR"
  info "Downloading uv..."
  curl -LsSf "$url" -o "${tmpdir}/${archive}" || fail "failed to download uv"
  tar -xzf "${tmpdir}/${archive}" -C "$tmpdir" || fail "failed to extract uv"
  found_uv=$(find "$tmpdir" -type f -name uv | head -n 1)
  [ -n "$found_uv" ] || fail "uv binary not found in archive"
  cp "$found_uv" "$UV_BIN"
  chmod +x "$UV_BIN"
  info "Installed uv: ${UV_BIN}"
}

normalize_version_ref() {
  value="$1"
  value=${value#v}
  case "$value" in
    *[!0-9A-Za-z.+!-]*|"") fail "invalid install version: $1" ;;
  esac
  printf 'v%s' "$value"
}

classify_ref_kind() {
  value="$1"
  if [ "$value" = "main" ]; then
    printf 'main'
  elif printf '%s' "$value" | grep -Eq '^v?[0-9]+([.][0-9A-Za-z.+!-]+)*$'; then
    printf 'release'
  else
    printf 'custom_ref'
  fi
}

resolve_latest_release_tag() {
  curl -LsSf "https://api.github.com/repos/${REPO}/releases/latest" \
    | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    | head -n 1 || true
}

resolve_ref() {
  selector_count=0
  [ -n "${RECOLLECTIUM_INSTALL_VERSION:-}" ] && selector_count=$((selector_count + 1))
  [ -n "${RECOLLECTIUM_INSTALL_MAIN:-}" ] && selector_count=$((selector_count + 1))
  [ -n "${RECOLLECTIUM_INSTALL_REF:-}" ] && selector_count=$((selector_count + 1))
  [ "$selector_count" -le 1 ] || fail "set only one of RECOLLECTIUM_INSTALL_VERSION, RECOLLECTIUM_INSTALL_MAIN, or RECOLLECTIUM_INSTALL_REF"

  TRACKING_KIND="latest_release"
  TRACKING_SELECTOR="latest"
  TRACKING_VERSION=""
  RESOLVED_RELEASE_URL=""

  if [ "${RECOLLECTIUM_INSTALL_MAIN:-}" = "1" ] || [ "${RECOLLECTIUM_INSTALL_MAIN:-}" = "true" ] || [ "${RECOLLECTIUM_INSTALL_MAIN:-}" = "yes" ]; then
    TRACKING_KIND="main"
    TRACKING_SELECTOR="main"
    if [ -n "${RECOLLECTIUM_INSTALL_RESOLVED_REF:-}" ]; then
      RESOLVED_REF="$RECOLLECTIUM_INSTALL_RESOLVED_REF"
    else
      RESOLVED_REF="main"
    fi
    return
  fi

  if [ -n "${RECOLLECTIUM_INSTALL_VERSION:-}" ]; then
    if [ "$(printf '%s' "$RECOLLECTIUM_INSTALL_VERSION" | tr '[:upper:]' '[:lower:]')" = "latest" ]; then
      TRACKING_KIND="latest_release"
      TRACKING_SELECTOR="latest"
      if [ -n "${RECOLLECTIUM_INSTALL_RESOLVED_REF:-}" ]; then
        RESOLVED_REF="$RECOLLECTIUM_INSTALL_RESOLVED_REF"
        return
      fi
    else
      ref=$(normalize_version_ref "$RECOLLECTIUM_INSTALL_VERSION")
      TRACKING_KIND="release"
      TRACKING_SELECTOR="$ref"
      TRACKING_VERSION="${ref#v}"
      RESOLVED_REF="$ref"
      return
    fi
  elif [ -n "${RECOLLECTIUM_INSTALL_REF:-}" ]; then
    kind=$(classify_ref_kind "$RECOLLECTIUM_INSTALL_REF")
    TRACKING_KIND="$kind"
    TRACKING_SELECTOR="$RECOLLECTIUM_INSTALL_REF"
    [ "$kind" = "release" ] && TRACKING_VERSION="${RECOLLECTIUM_INSTALL_REF#v}"
    RESOLVED_REF="$RECOLLECTIUM_INSTALL_REF"
    return
  fi

  tag=$(resolve_latest_release_tag)
  if [ -n "$tag" ]; then
    RESOLVED_REF="$tag"
  else
    fail "failed to resolve latest GitHub release; set RECOLLECTIUM_INSTALL_MAIN=1 to install main"
  fi
}

append_managed_path_edit() {
  path="$1"
  case "
${MANAGED_PATH_EDITS}
" in
    *"
${path}
"*) return ;;
  esac
  MANAGED_PATH_EDITS="${MANAGED_PATH_EDITS}${path}
"
}

ensure_path_file() {
  profile="$1"
  line="export PATH=\"${TOOL_BIN_DIR}:\$PATH\""
  start_marker="# >>> recollectium path >>>"
  end_marker="# <<< recollectium path <<<"

  if [ -f "$profile" ]; then
    if grep -F "$start_marker" "$profile" >/dev/null 2>&1; then
      tmp=$(mktemp "${profile}.recollectium.XXXXXX") || fail "failed to create temporary path profile"
      has_end=0
      grep -F "$end_marker" "$profile" >/dev/null 2>&1 && has_end=1
      awk -v start="$start_marker" -v end="$end_marker" -v path_line="$line" -v has_end="$has_end" '
        function print_path_block() {
          if (!printed_path_block) {
            print start
            print path_line
            print end
            printed_path_block = 1
          }
        }
        in_path_block {
          if ($0 == end) {
            in_path_block = 0
          }
          next
        }
        $0 == start {
          print_path_block()
          if (has_end == "1") {
            in_path_block = 1
          }
          next
        }
        $0 == path_line {
          next
        }
        { print }
      ' "$profile" > "$tmp" || {
        rm -f "$tmp"
        fail "failed to repair Recollectium PATH block in ${profile}"
      }
      mv "$tmp" "$profile" || fail "failed to update Recollectium PATH block in ${profile}"
      append_managed_path_edit "$profile"
      return
    fi
    if grep -F "$line" "$profile" >/dev/null 2>&1; then
      append_managed_path_edit "$profile"
      return
    fi
  else
    parent=$(dirname "$profile")
    mkdir -p "$parent"
  fi

  printf '\n%s\n%s\n%s\n' "$start_marker" "$line" "$end_marker" >> "$profile"
  append_managed_path_edit "$profile"
}

ensure_path_hint() {
  [ -n "$TOOL_BIN_DIR" ] || fail "uv tool bin directory was not resolved"
  case ":${ORIGINAL_PATH}:" in
    *":${TOOL_BIN_DIR}:"*) return ;;
  esac

  detected_shell="${SHELL##*/}"
  if [ "$detected_shell" = "zsh" ]; then
    zdotdir="${ZDOTDIR:-$HOME}"
    ensure_path_file "${zdotdir}/.zprofile"
    ensure_path_file "${zdotdir}/.zshrc"
    info "Added ${TOOL_BIN_DIR} to ${zdotdir}/.zprofile and ${zdotdir}/.zshrc for future shells."
  else
    profile="${HOME}/.profile"
    ensure_path_file "$profile"
    info "Added ${TOOL_BIN_DIR} to ${profile} for future shells."
  fi
}

resolve_tool_bin_dir() {
  TOOL_BIN_DIR=$("$UV_BIN" tool dir --bin 2>/dev/null || true)
  [ -n "$TOOL_BIN_DIR" ] || fail "failed to resolve uv tool bin directory"
  [ -d "$TOOL_BIN_DIR" ] || mkdir -p "$TOOL_BIN_DIR"
}

verify_installed_tool() {
  [ -n "$TOOL_BIN_DIR" ] || fail "uv tool bin directory was not resolved"
  command_path="${TOOL_BIN_DIR}/recollectium"
  if [ ! -x "$command_path" ]; then
    fail "recollectium executable was not installed in uv tool bin directory: ${TOOL_BIN_DIR}"
  fi
}

recollectium_stdout_is_tty() {
  [ -t 1 ]
}

guidance_supports_color() {
  [ -z "${NO_COLOR:-}" ] && recollectium_stdout_is_tty
}

guidance_info() {
  message="$1"
  if guidance_supports_color; then
    printf '\033[32m%s\033[0m\n' "$message"
  else
    printf '%s\n' "$message"
  fi
}

guidance_warning() {
  message="$1"
  if guidance_supports_color; then
    printf '\033[33m%s\033[0m\n' "$message"
  else
    printf '%s\n' "$message"
  fi
}

expected_recollectium_path() {
  printf '%s/recollectium' "$TOOL_BIN_DIR"
}

current_path_resolves_installed_tool() {
  expected=$(expected_recollectium_path)
  resolved=$(PATH="$ORIGINAL_PATH" command -v recollectium 2>/dev/null || true)
  [ "$resolved" = "$expected" ]
}

future_shell_resolves_installed_tool() {
  expected=$(expected_recollectium_path)
  sentinel="__recollectium_path_check_$$__"
  check_command="printf '%s\n' '${sentinel}'; command -v recollectium; printf '%s\n' '${sentinel}'"
  for shell_name in zsh bash fish; do
    shell_path=$(PATH="$ORIGINAL_PATH" command -v "$shell_name" 2>/dev/null || true)
    [ -n "$shell_path" ] || continue
    if [ "$shell_name" = "fish" ]; then
      output=$(PATH="$ORIGINAL_PATH" "$shell_path" -lc "$check_command" 2>/dev/null || true)
    else
      output=$(PATH="$ORIGINAL_PATH" "$shell_path" -lic "$check_command" 2>/dev/null || true)
    fi
    resolved=""
    seen_sentinel=0
    while IFS= read -r output_line; do
      if [ "$output_line" = "$sentinel" ]; then
        if [ "$seen_sentinel" -eq 0 ]; then
          seen_sentinel=1
          continue
        fi
        break
      fi
      if [ "$seen_sentinel" -eq 1 ] && [ -z "$resolved" ] && [ -n "$output_line" ]; then
        resolved="$output_line"
      fi
    done <<EOF
$output
EOF
    [ "$resolved" = "$expected" ] && return 0
  done
  return 1
}

current_terminal_path_command() {
  guidance_shell="${COMPLETION_SHELL:-${SHELL##*/}}"
  if [ "$guidance_shell" = "fish" ]; then
    printf 'set -gx PATH "%s" $PATH' "$TOOL_BIN_DIR"
  else
    printf 'export PATH="%s:$PATH"' "$TOOL_BIN_DIR"
  fi
}

print_managed_path_edits() {
  [ -n "$MANAGED_PATH_EDITS" ] || return 0
  summary=""
  while IFS= read -r path_edit; do
    [ -n "$path_edit" ] || continue
    if [ -n "$summary" ]; then
      summary="${summary}, ${path_edit}"
    else
      summary="$path_edit"
    fi
  done <<EOF
$MANAGED_PATH_EDITS
EOF
  [ -n "$summary" ] && guidance_warning "Managed PATH files updated: ${summary}"
}

print_final_guidance() {
  if current_path_resolves_installed_tool; then
    guidance_info "Recollectium installed."
    guidance_info "Verify with: recollectium --version"
    return
  fi

  path_command=$(current_terminal_path_command)
  if future_shell_resolves_installed_tool; then
    guidance_info "Recollectium installed."
    guidance_warning "Open a new terminal window before using recollectium, or run this command in the current terminal:"
    guidance_warning "  ${path_command}"
    guidance_warning "Then verify with: recollectium --version"
    return
  fi

  if [ -n "$MANAGED_PATH_EDITS" ]; then
    guidance_warning "Recollectium installed. PATH files were updated, but PATH setup could not be verified for a future shell."
    print_managed_path_edits
    guidance_warning "Restart your terminal, or run this command in the current terminal:"
    guidance_warning "  ${path_command}"
  else
    guidance_warning "Recollectium installed, but PATH setup could not be verified."
    guidance_warning "Add Recollectium to your shell startup file:"
    guidance_warning "  ${path_command}"
    guidance_warning "Then restart your terminal, or run the command above in the current terminal."
  fi
  guidance_warning "Then verify with: recollectium --version"
}

resolve_install_state_dir() {
  case "$(uname -s)" in
    Darwin)
      if [ -n "${XDG_STATE_HOME:-}" ]; then
        printf '%s/recollectium' "$XDG_STATE_HOME"
      else
        printf '%s/Library/Application Support/recollectium' "$HOME"
      fi
      ;;
    *)
      printf '%s/recollectium' "${XDG_STATE_HOME:-${HOME}/.local/state}"
      ;;
  esac
}

record_install_metadata() {
  state_dir=$(resolve_install_state_dir)
  metadata_path="${state_dir}/install.json"
  installed_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
  mkdir -p "$state_dir"
  escaped_ref=$(json_escape "$ref")
  escaped_kind=$(json_escape "$TRACKING_KIND")
  escaped_selector=$(json_escape "$TRACKING_SELECTOR")
  escaped_repo=$(json_escape "$REPO")
  ref_kind="$TRACKING_KIND"
  if [ "$TRACKING_KIND" = "latest_release" ]; then
    ref_kind="release"
  fi
  escaped_ref_kind=$(json_escape "$ref_kind")

  path_edits="["
  first_path_edit=1
  if [ -n "$MANAGED_PATH_EDITS" ]; then
    while IFS= read -r path_edit; do
      [ -n "$path_edit" ] || continue
      escaped_path_edit=$(json_escape "$path_edit")
      if [ "$first_path_edit" -eq 1 ]; then
        first_path_edit=0
      else
        path_edits="${path_edits}, "
      fi
      path_edits="${path_edits}\"${escaped_path_edit}\""
    done <<EOF
$MANAGED_PATH_EDITS
EOF
  fi
  path_edits="${path_edits}]"

  completion_edits="["
  if [ -n "$COMPLETION_RC" ]; then
    escaped_completion_path=$(json_escape "$COMPLETION_RC")
    escaped_completion_shell=$(json_escape "$COMPLETION_SHELL")
    completion_edits="${completion_edits}{\"shell\": \"${escaped_completion_shell}\", \"path\": \"${escaped_completion_path}\", \"source_command\": \"recollectium completion --source ${escaped_completion_shell}\"}"
  fi
  completion_edits="${completion_edits}]"

  tracking_target="{\"kind\": \"${escaped_kind}\", \"selector\": \"${escaped_selector}\", \"repo\": \"${escaped_repo}\""
  if [ -n "$TRACKING_VERSION" ]; then
    escaped_version=$(json_escape "$TRACKING_VERSION")
    tracking_target="${tracking_target}, \"version\": \"${escaped_version}\", \"ref\": \"${escaped_ref}\""
  elif [ "$TRACKING_KIND" = "main" ]; then
    escaped_tracking_ref=$(json_escape "$TRACKING_SELECTOR")
    tracking_target="${tracking_target}, \"ref\": \"${escaped_tracking_ref}\""
  elif [ "$TRACKING_KIND" != "latest_release" ]; then
    tracking_target="${tracking_target}, \"ref\": \"${escaped_ref}\""
  fi
  tracking_target="${tracking_target}}"

  last_resolved="{\"ref\": \"${escaped_ref}\", \"resolved_at\": \"${installed_at}\""
  if [ -n "$TRACKING_VERSION" ]; then
    last_resolved="${last_resolved}, \"version\": \"$(json_escape "$TRACKING_VERSION")\""
  fi
  last_resolved="${last_resolved}}"

  printf '{\n  "metadata_version": 2,\n  "install_method": "bootstrap",\n  "source_ref": "%s",\n  "source_ref_kind": "%s",\n  "source_repo": "%s",\n  "installed_at": "%s",\n  "updated_at": "%s",\n  "tracking_target": %s,\n  "last_resolved": %s,\n  "managed_path_edits": %s,\n  "managed_completion_edits": %s\n}\n' "$escaped_ref" "$escaped_ref_kind" "$escaped_repo" "$installed_at" "$installed_at" "$tracking_target" "$last_resolved" "$path_edits" "$completion_edits" > "$metadata_path"
}

configure_shell_completion() {
  detected_shell="${SHELL##*/}"
  case "$detected_shell" in
    bash) shell="bash"; rc="${HOME}/.bashrc" ;;
    zsh)  shell="zsh"; rc="${HOME}/.zshrc" ;;
    fish) shell="fish"; rc="${HOME}/.config/fish/config.fish" ;;
    *)    shell="bash"; rc="${HOME}/.bashrc" ;;  # default to bash per spec
  esac

  PATH="${TOOL_BIN_DIR}:${INSTALL_DIR}:$PATH" "$UV_BIN" tool run --from "$package" recollectium completion --install "$shell" --yes >/dev/null \
    || fail "failed to configure shell completion"
  COMPLETION_RC="$rc"
  COMPLETION_SHELL="$shell"
  info "Shell completion configured in ${rc}."
}

install_uv
resolve_ref
ref="$RESOLVED_REF"
package="git+https://github.com/${REPO}.git@${ref}"
resolve_tool_bin_dir
PATH="${TOOL_BIN_DIR}:${ORIGINAL_PATH}"
export PATH
info "Installing Recollectium from ${ref}..."
"$UV_BIN" tool install --python 3.12 --force "$package"
verify_installed_tool
info "Maintaining embeddings (config, database, model, stale memories)..."
"$UV_BIN" tool run --from "$package" recollectium embedding-maintenance
ensure_path_hint
configure_shell_completion
record_install_metadata
print_final_guidance

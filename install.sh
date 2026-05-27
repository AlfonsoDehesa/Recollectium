#!/bin/sh
set -eu

REPO="AlfonsoDehesa/recallium"
INSTALL_DIR="${HOME}/.local/bin"
UV_BIN="${INSTALL_DIR}/uv"

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

resolve_ref() {
  if [ -n "${RECALLIUM_INSTALL_REF:-}" ]; then
    printf '%s' "$RECALLIUM_INSTALL_REF"
    return
  fi

  tag=$(curl -LsSf "https://api.github.com/repos/${REPO}/releases/latest" \
    | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    | head -n 1 || true)
  if [ -n "$tag" ]; then
    printf '%s' "$tag"
  else
    info "No GitHub release found; installing from main."
    printf 'main'
  fi
}

ensure_path_hint() {
  case ":${PATH}:" in
    *":${INSTALL_DIR}:"*) return ;;
  esac

  profile="${HOME}/.profile"
  line="export PATH=\"${INSTALL_DIR}:\$PATH\""
  if [ ! -f "$profile" ] || ! grep -F "$line" "$profile" >/dev/null 2>&1; then
    printf '\n# Recallium CLI\n%s\n' "$line" >> "$profile"
  fi
  info "Added ${INSTALL_DIR} to ${profile}. Restart your shell if recallium is not found."
}

install_uv
ref=$(resolve_ref)
package="git+https://github.com/${REPO}.git@${ref}"
info "Installing Recallium from ${ref}..."
"$UV_BIN" tool install --python 3.12 --force "$package"
ensure_path_hint
info "Recallium installed. Try: recallium --version"

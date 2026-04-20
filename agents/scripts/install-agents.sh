#!/usr/bin/env bash

set -euo pipefail

TARGET=""
DEST="."
REF="main"
FORCE=0
REPO="GriffinBoris/Agents"

usage() {
  cat <<'EOF'
Usage: ./agents/scripts/install-agents.sh --target <source|opencode|claude|copilot|codex|gemini> [--dest <project-root>] [--ref <git-ref>] [--force] [--repo <owner/repo|https-url|local-path>]
EOF
}

normalize_repo_slug() {
  local repo_value="$1"

  if [[ "$repo_value" =~ ^https://github.com/([^/]+/[^/]+?)(\.git)?/?$ ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
    return 0
  fi

  printf '%s\n' "$repo_value"
}

resolve_path() {
  local path_value="$1"

  if [[ "$path_value" = /* ]]; then
    printf '%s\n' "$path_value"
    return 0
  fi

  printf '%s\n' "$(pwd)/$path_value"
}

download_repo_archive() {
  local repo_value="$1"
  local ref_value="$2"
  local temp_root="$3"

  local repo_slug
  repo_slug="$(normalize_repo_slug "$repo_value")"
  local archive_path="$temp_root/repo.tar.gz"
  local extract_root="$temp_root/extract"

  mkdir -p "$extract_root"
  curl -fsSL "https://codeload.github.com/${repo_slug}/tar.gz/${ref_value}" -o "$archive_path"
  tar -xzf "$archive_path" -C "$extract_root"

  local source_root=""
  local entry
  for entry in "$extract_root"/*; do
    if [[ -d "$entry" ]]; then
      source_root="$entry"
      break
    fi
  done

  if [[ -z "$source_root" ]]; then
    printf 'Unable to locate extracted repository contents.\n' >&2
    exit 1
  fi

  printf '%s\n' "$source_root"
}

copy_install_files() {
  local install_root="$1"
  local destination_root="$2"

  while IFS= read -r -d '' source_file; do
    if [[ "$(basename "$source_file")" == "README.md" ]]; then
      continue
    fi

    local relative_path="${source_file#${install_root}/}"
    local destination_file="$destination_root/$relative_path"
    mkdir -p "$(dirname "$destination_file")"
    cp -f "$source_file" "$destination_file"
    printf 'OK: installed %s\n' "$destination_file"
  done < <(find "$install_root" -type f -print0)
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="${2:-}"
      shift 2
      ;;
    --dest)
      DEST="${2:-}"
      shift 2
      ;;
    --ref)
      REF="${2:-}"
      shift 2
      ;;
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  printf 'Missing required --target argument.\n' >&2
  usage >&2
  exit 1
fi

case "$TARGET" in
  source|opencode|claude|copilot|codex|gemini)
    ;;
  *)
    printf 'Unsupported target: %s\n' "$TARGET" >&2
    exit 1
    ;;
esac

DEST="$(resolve_path "$DEST")"

tmp_root="$(mktemp -d)"
cleanup() {
  rm -rf "$tmp_root"
}
trap cleanup EXIT

if [[ -d "$REPO" ]]; then
  source_root="$(resolve_path "$REPO")"
else
  source_root="$(download_repo_archive "$REPO" "$REF" "$tmp_root")"
fi

if [[ "$TARGET" == "source" ]]; then
  install_root="$source_root"
  destination_root="$DEST"
else
  install_root="$source_root/dist/$TARGET"
  destination_root="$DEST"
fi

if [[ "$TARGET" == "source" ]]; then
  install_files=()
  for relative_path in "agents"; do
    if [[ -e "$install_root/$relative_path" ]]; then
      install_files+=("$relative_path")
    fi
  done

  if [[ ${#install_files[@]} -eq 0 ]]; then
    printf 'Install source does not exist: %s\n' "$install_root" >&2
    exit 1
  fi

  mkdir -p "$destination_root"
  for relative_path in "${install_files[@]}"; do
    source_path="$install_root/$relative_path"
    destination_path="$destination_root/$relative_path"
    if [[ -d "$source_path" ]]; then
      mkdir -p "$destination_path"
      while IFS= read -r -d '' nested_source_file; do
        if [[ "$(basename "$nested_source_file")" == "README.md" ]]; then
          continue
        fi

        nested_relative="${nested_source_file#${source_path}/}"
        nested_destination="$destination_path/$nested_relative"
        mkdir -p "$(dirname "$nested_destination")"
        cp -f "$nested_source_file" "$nested_destination"
        printf 'OK: installed %s\n' "$nested_destination"
      done < <(find "$source_path" -type f ! -path '*/__pycache__/*' ! -name '*.pyc' -print0)
    else
      mkdir -p "$(dirname "$destination_path")"
      cp -f "$source_path" "$destination_path"
      printf 'OK: installed %s\n' "$destination_path"
    fi
  done

  exit 0
fi

if [[ ! -d "$install_root" ]]; then
  printf 'Install source does not exist: %s\n' "$install_root" >&2
  exit 1
fi

mkdir -p "$destination_root"

copy_install_files "$install_root" "$destination_root"

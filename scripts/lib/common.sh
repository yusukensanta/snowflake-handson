#!/usr/bin/env bash
# Shared helpers. Source from scripts: . "$(dirname "$0")/lib/common.sh"
DRY_RUN="${DRY_RUN:-0}"
log_info() { printf '[info] %s\n' "$*"; }
log_err()  { printf '[error] %s\n' "$*" >&2; }
require_cmd() { command -v "$1" >/dev/null 2>&1 || { log_err "missing command: $1 (run scripts/install-tools)"; return 1; }; }
# parse_common_flags "$@": sets DRY_RUN=1 for --dry-run; leaves other args in REST_ARGS.
parse_common_flags() {
  REST_ARGS=()
  for a in "$@"; do
    case "$a" in --dry-run) DRY_RUN=1 ;; *) REST_ARGS+=("$a") ;; esac
  done
}
# run CMD...: print instead of executing under DRY_RUN=1.
run() {
  if [ "$DRY_RUN" = "1" ]; then printf '[dry-run] %s\n' "$*"; else "$@"; fi
}

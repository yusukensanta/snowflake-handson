#!/usr/bin/env bash
# Shared helpers. Source from scripts: . "$(dirname "$0")/lib/common.sh"
# Scripts preview by default; only the --execute argument enables changes. The flags below are assigned unconditionally so
# that nothing exported in the caller's shell (e.g. DRY_RUN=0) can switch a script into execute mode.
DRY_RUN=1                  # 1 = change nothing; 0 only after --execute
PRINT_ONLY=0               # 1 only after --dry-run: read-only code prints its checks instead of running them
PREVIEW_HINT="--execute"   # flags named in the closing line of a preview
log_info() { printf '[info] %s\n' "$*"; }
log_err()  { printf '[error] %s\n' "$*" >&2; }
require_cmd() { command -v "$1" >/dev/null 2>&1 || { log_err "missing command: $1 (run scripts/install-tools --execute)"; return 1; }; }
# parse_common_flags "$@": handles --execute and --dry-run, leaves other args in REST_ARGS, and arranges the closing
# preview line. Read-only code calls mark_read_only afterwards.
parse_common_flags() {
  local a execute=0
  DRY_RUN=1; PRINT_ONLY=0; REST_ARGS=()
  for a in "$@"; do
    case "$a" in --execute) execute=1 ;; --dry-run) PRINT_ONLY=1 ;; *) REST_ARGS+=("$a") ;; esac
  done
  if [ "$execute" = "1" ]; then
    [ "$PRINT_ONLY" = "0" ] || { log_err "--execute and --dry-run cannot be combined"; exit 64; }
    DRY_RUN=0
  fi
  trap _preview_footer EXIT
}
# Only after success: a failed preview already ends with its error.
_preview_footer() {
  local rc=$?
  if [ "$rc" -eq 0 ] && [ "$DRY_RUN" = "1" ]; then
    printf '[preview] nothing was changed. Re-run with %s to apply.\n' "$PREVIEW_HINT"
  fi
}
# mark_read_only: this script (or mode) changes nothing, so there is no preview to announce.
mark_read_only() { trap - EXIT; }
# done_msg MSG: report finished work; silent in a preview so it cannot be mistaken for a completed action.
done_msg() { if [ "$DRY_RUN" = "0" ]; then log_info "$*"; fi; }
# run CMD...: print instead of executing unless --execute was given.
run() {
  if [ "$DRY_RUN" = "1" ]; then printf '[dry-run] %s\n' "$*"; else "$@"; fi
}
# Per-warehouse resource monitors as "WAREHOUSE:CREDIT_QUOTA". Only ACCOUNTADMIN can create a monitor or attach it to a
# warehouse, so scripts/bootstrap creates them and scripts/attach-monitors attaches them; Terraform (TF_ADMIN) does neither.
# Keep the warehouse names in sync with local.warehouse_monitors in terraform/envs/handson/main.tf (tests/test_monitors_sync.py).
# shellcheck disable=SC2034  # used by the scripts that source this file
WAREHOUSE_MONITORS="LOAD_WH:10 TRANSFORM_WH:10 BI_WH:10 MONITOR_WH:5"

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
# Per-warehouse resource monitors as "WAREHOUSE:CREDIT_QUOTA". Only ACCOUNTADMIN can create a monitor or attach it to a
# warehouse, so scripts/bootstrap creates them and scripts/attach-monitors attaches them; Terraform (TF_ADMIN) does neither.
# Keep the warehouse names in sync with local.warehouse_monitors in terraform/envs/handson/main.tf (tests/test_monitors_sync.py).
# shellcheck disable=SC2034  # used by the scripts that source this file
WAREHOUSE_MONITORS="LOAD_WH:10 TRANSFORM_WH:10 BI_WH:10 MONITOR_WH:5"

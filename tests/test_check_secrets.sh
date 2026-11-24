#!/usr/bin/env bash
# Behavioural test for scripts/check-secrets (Review Focus 4).
set -u
here="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
fail=0
printf '%s\n' '-----BEGIN PRIVATE KEY-----' 'abc' > "$tmp/leak.txt"
if "$here/scripts/check-secrets" "$tmp" >/dev/null 2>&1; then echo "FAIL: private key not detected"; fail=1; fi
rm "$tmp/leak.txt"
printf '%s\n' 'account: myorg-myacct.snowflakecomputing.com' > "$tmp/host.txt"
if "$here/scripts/check-secrets" "$tmp" >/dev/null 2>&1; then echo "FAIL: account host not detected"; fail=1; fi
rm "$tmp/host.txt"
printf '%s\n' 'password = "hunter2hunter2"' > "$tmp/pw.txt"
if "$here/scripts/check-secrets" "$tmp" >/dev/null 2>&1; then echo "FAIL: password assignment not detected"; fail=1; fi
rm "$tmp/pw.txt"
printf '%s\n' 'nothing secret here; use ~/.snowflake/connections.toml' > "$tmp/ok.txt"
if ! "$here/scripts/check-secrets" "$tmp" >/dev/null 2>&1; then echo "FAIL: clean dir flagged"; fail=1; fi
[ "$fail" -eq 0 ] && echo "PASS: check-secrets" || exit 1

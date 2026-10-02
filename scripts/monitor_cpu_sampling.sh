#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MONITOR_SCRIPT="$ROOT_DIR/scripts/monitor.sh"

DURATION="${DURATION:-30}"
INTERVAL="${INTERVAL:-0.1}"
count="$(python3 - "$DURATION" "$INTERVAL" <<'PY'
import math
import sys

duration, interval = map(float, sys.argv[1:3])
if not math.isfinite(duration) or not math.isfinite(interval) or duration <= 0 or interval <= 0:
    raise SystemExit("duration and interval must be finite positive numbers")
count = max(1, int(math.ceil(duration / interval)))
print(count)
PY
)"

if [ "$#" -eq 0 ]; then
  mkdir -p "$ROOT_DIR/.runtime/cpu-samples"
  OUT_DIR="$(mktemp -d "$ROOT_DIR/.runtime/cpu-samples/run-XXXXXXXX")"
  OUT_FILE="$OUT_DIR/monitor_cpu.log"
elif [ "$#" -eq 2 ] && [ "$1" = --output ]; then
  OUT_FILE="$2"
  mkdir -p "$(dirname "$OUT_FILE")"
else
  printf 'Usage: %s [--output NEW_FILE]\n' "$0" >&2
  exit 2
fi
# Noclobber also rejects a file created after argument validation.
( set -C; : > "$OUT_FILE" ) || { printf '[ERROR] output file must be new\n' >&2; exit 2; }

echo "[INFO] Sampling CPU: duration=${DURATION}s interval=${INTERVAL}s count=${count}"

i=1
while [ "$i" -le "$count" ]; do
  MONITOR_LOG_FILE="$OUT_FILE" MONITOR_CPU_INTERVAL="$INTERVAL" MONITOR_TCP_CONNECT_CHECK=0 "$MONITOR_SCRIPT"
  i=$((i + 1))
done

echo "[INFO] Saved samples to $OUT_FILE"

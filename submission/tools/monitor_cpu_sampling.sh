#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MONITOR_SCRIPT="$ROOT_DIR/monitor.sh"

DURATION="${DURATION:-30}"
INTERVAL="${INTERVAL:-1}"
OUT_DIR="$ROOT_DIR/evidence/cpu/spike"
OUT_FILE="$OUT_DIR/monitor_cpu.log"

mkdir -p "$OUT_DIR"
: > "$OUT_FILE"

count="$(python3 - <<'PY'
import math
import os

duration = float(os.environ.get("DURATION", "30"))
interval = float(os.environ.get("INTERVAL", "1"))
if interval <= 0:
    interval = 1.0
count = max(1, int(math.ceil(duration / interval)))
print(count)
PY
)"

echo "[INFO] Sampling CPU: duration=${DURATION}s interval=${INTERVAL}s count=${count}"

i=1
while [ "$i" -le "$count" ]; do
  MONITOR_LOG_FILE="$OUT_FILE" MONITOR_CPU_INTERVAL="$INTERVAL" "$MONITOR_SCRIPT"
  i=$((i + 1))
done

echo "[INFO] Saved samples to $OUT_FILE"
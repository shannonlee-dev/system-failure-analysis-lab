#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP="$ROOT_DIR/assets/agent-app-leak/agent-app-leak"
MONITOR="$ROOT_DIR/scripts/monitor.sh"
PORT="${AGENT_PORT:-15034}"
if [ "$#" -eq 0 ]; then
  mkdir -p "$ROOT_DIR/.runtime/collections"
  EVIDENCE_DIR="$(mktemp -d "$ROOT_DIR/.runtime/collections/run-XXXXXXXX")"
elif [ "$#" -eq 2 ] && [ "$1" = --output ]; then
  EVIDENCE_DIR="$2"
  mkdir -p "$(dirname "$EVIDENCE_DIR")"
  mkdir "$EVIDENCE_DIR" || { printf '[ERROR] output directory must be new\n' >&2; exit 2; }
else
  printf 'Usage: %s [--output NEW_DIRECTORY]\n' "$0" >&2
  exit 2
fi
RUN_ROOT="$(mktemp -d)"
ACTIVE_PID=""
COLLECTION_FAILURES=0
printf '[collect] output=%s\n' "$EVIDENCE_DIR"

if [ ! -x "$APP" ] && [ -f "${APP}.zip" ]; then
  python3 - "$APP" "${APP}.zip" <<'PY'
import os
import platform
import sys
import zipfile

target, archive = sys.argv[1:3]
machine = platform.machine().lower()
member = "agent-leak-app-arm64" if machine in {"aarch64", "arm64"} else "agent-leak-app-x86"

with zipfile.ZipFile(archive) as zf:
    data = zf.read(member)

os.makedirs(os.path.dirname(target), exist_ok=True)
with open(target, "wb") as f:
    f.write(data)
os.chmod(target, 0o750)
PY
fi

if [ ! -x "$APP" ]; then
  printf '[ERROR] target app is not executable: %s\n' "$APP" >&2
  exit 1
fi

kill_tree() {
  local pid="$1"
  local child

  while read -r child; do
    [ -n "$child" ] || continue
    kill_tree "$child"
  done < <(pgrep -P "$pid" 2>/dev/null || true)

  kill "$pid" 2>/dev/null || true
}

cleanup() {
  if [ -n "$ACTIVE_PID" ]; then
    kill_tree "$ACTIVE_PID"
    wait "$ACTIVE_PID" 2>/dev/null || true
  fi
  rm -rf "$RUN_ROOT"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
{
  printf 'collected_at=%s\n' "$(date -Iseconds)"
  printf 'platform=%s\n' "$(uname -sm)"
  printf 'binary_sha256=%s\n' "$(sha256sum "$APP" | cut -d' ' -f1)"
} > "$EVIDENCE_DIR/run-metadata.txt"

wait_for_ready_or_exit() {
  local pid="$1"
  local stdout_file="$2"
  local waited=0

  while [ "$waited" -lt 80 ]; do
    if grep -q 'Agent READY' "$stdout_file" 2>/dev/null; then
      return 0
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
      return 1
    fi
    sleep 0.1
    waited=$((waited + 1))
  done

  return 1
}

write_ps_top_sample() {
  local pid="$1"
  local out_file="$2"
  local sample_status=0
  local code=0
  local children=""
  local top_output=""

  {
    printf -- '--- ps sample ---\n'
    ps -o pid,ppid,stat,pcpu,pmem,rss,comm,args -p "$pid" 2>&1 || {
      code=$?; sample_status=1; printf 'ps exit_code=%s\n' "$code";
    }
    children="$(pgrep -P "$pid" 2>/dev/null)" || true
    if [ -n "$children" ]; then
      printf '%s\n' "$children" | xargs -r ps -o pid,ppid,stat,pcpu,pmem,rss,comm,args -p 2>&1 || {
        code=$?; sample_status=1; printf 'child_ps exit_code=%s\n' "$code";
      }
    fi
    printf -- '\n--- top sample ---\n'
    top_output="$(top -b -n 1 -p "$pid" 2>&1)" || {
      code=$?; sample_status=1; printf 'top exit_code=%s\n' "$code";
    }
    printf '%s\n' "$top_output" | sed -n '1,12p'
    printf '\n'
  } >> "$out_file"
  return "$sample_status"
}

run_boot_failed() {
  local target="$EVIDENCE_DIR/boot-failed"
  local home="$RUN_ROOT/boot-failed-home"

  mkdir -p "$target" "$home/upload_files" "$home/api_keys" "$target"
  printf 'wrong_key\n' > "$home/api_keys/secret.key"
  chmod 600 "$home/api_keys/secret.key"

  : > "$target/stdout.log"
  : > "$target/stderr.log"

  local app_exit=0
  AGENT_HOME="$home" \
  AGENT_PORT="$PORT" \
  AGENT_UPLOAD_DIR="$home/upload_files" \
  AGENT_KEY_PATH="$home/api_keys" \
  AGENT_LOG_DIR="$target" \
  MEMORY_LIMIT=256 \
  CPU_MAX_OCCUPY=10 \
  MULTI_THREAD_ENABLE=false \
  "$APP" > "$target/stdout.log" 2> "$target/stderr.log" || app_exit=$?
  printf 'app_exit_code=%s\n' "$app_exit" > "$target/exit-status.txt"
}

run_scenario() {
  local name="$1"
  local rel_target="$2"
  local memory="$3"
  local cpu="$4"
  local multi="$5"
  local duration="$6"
  local monitor_count="${7:-0}"
  local ps_count="${8:-0}"

  local target="$EVIDENCE_DIR/$rel_target"
  local home="$RUN_ROOT/$name-home"
  local stdout_file="$target/stdout.log"
  local stderr_file="$target/stderr.log"
  local monitor_stdout="$target/monitor.stdout"
  local monitor_log="$target/monitor.log"
  local ps_top="$target/ps_top.log"

  case "$rel_target" in
    deadlock/*)
      ps_top="$target/thread_samples.log"
      ;;
  esac

  mkdir -p "$target" "$home/upload_files" "$home/api_keys"
  printf 'agent_api_key_test\n' > "$home/api_keys/secret.key"
  chmod 600 "$home/api_keys/secret.key"

  : > "$stdout_file"
  : > "$stderr_file"
  : > "$target/agent_app.log"
  if [ "$monitor_count" -gt 0 ]; then
    : > "$monitor_stdout"
    : > "$monitor_log"
  fi
  if [ "$ps_count" -gt 0 ]; then
    : > "$ps_top"
  fi

  AGENT_HOME="$home" \
  AGENT_PORT="$PORT" \
  AGENT_UPLOAD_DIR="$home/upload_files" \
  AGENT_KEY_PATH="$home/api_keys" \
  AGENT_LOG_DIR="$target" \
  MEMORY_LIMIT="$memory" \
  CPU_MAX_OCCUPY="$cpu" \
  MULTI_THREAD_ENABLE="$multi" \
  "$APP" > "$stdout_file" 2> "$stderr_file" &

  local pid="$!"
  ACTIVE_PID="$pid"
  local ready_status=0
  local monitor_failures=0
  local process_sample_failures=0
  local stopped_by_collector=0
  local app_exit=0
  wait_for_ready_or_exit "$pid" "$stdout_file" || ready_status=$?

  local i=1
  while [ "$i" -le "$monitor_count" ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
      break
    fi
    AGENT_HOME="$home" \
    AGENT_PORT="$PORT" \
    AGENT_UPLOAD_DIR="$home/upload_files" \
    AGENT_KEY_PATH="$home/api_keys" \
    AGENT_LOG_DIR="$target" \
    AGENT_APP_PID="$pid" \
    MONITOR_LOG_FILE="$monitor_log" \
    MONITOR_CPU_INTERVAL=1 \
    "$MONITOR" >> "$monitor_stdout" 2>&1 || {
      printf 'sample=%s exit_code=%s\n' "$i" "$?" >> "$target/monitor-errors.txt"
      monitor_failures=$((monitor_failures + 1))
    }
    i=$((i + 1))
  done

  i=1
  while [ "$i" -le "$ps_count" ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
      break
    fi
    write_ps_top_sample "$pid" "$ps_top" || process_sample_failures=$((process_sample_failures + 1))
    sleep 1
    i=$((i + 1))
  done

  local waited=0
  while [ "$waited" -lt "$duration" ] && kill -0 "$pid" 2>/dev/null; do
    sleep 1
    waited=$((waited + 1))
  done

  if kill -0 "$pid" 2>/dev/null; then
    stopped_by_collector=1
    kill_tree "$pid"
  fi
  wait "$pid" 2>/dev/null || app_exit=$?
  ACTIVE_PID=""
  printf 'launcher_pid=%s\napp_exit_code=%s\nready_exit_code=%s\nmonitor_failures=%s\nprocess_sample_failures=%s\nstopped_by_collector=%s\n' \
    "$pid" "$app_exit" "$ready_status" "$monitor_failures" "$process_sample_failures" "$stopped_by_collector" > "$target/exit-status.txt"
  if [ "$ready_status" -ne 0 ] || [ "$monitor_failures" -ne 0 ] || [ "$process_sample_failures" -ne 0 ]; then
    return 1
  fi
}

echo '[collect] boot-failed'
run_boot_failed

echo '[collect] boot-ready'
run_scenario boot-ready boot-ready 512 10 false 8 1 0 || COLLECTION_FAILURES=$((COLLECTION_FAILURES + 1))

echo '[collect] scheduling-round-robin'
run_scenario scheduling-round-robin scheduling/round-robin 512 10 false 8 0 0 || COLLECTION_FAILURES=$((COLLECTION_FAILURES + 1))

echo '[collect] oom-memory-50'
run_scenario oom-memory-50 oom/memory-50 50 10 false 8 3 3 || COLLECTION_FAILURES=$((COLLECTION_FAILURES + 1))

echo '[collect] oom-memory-128'
run_scenario oom-memory-128 oom/memory-128 128 10 false 20 7 7 || COLLECTION_FAILURES=$((COLLECTION_FAILURES + 1))

echo '[collect] cpu-max-10'
run_scenario cpu-max-10 cpu/cpu-max-10 512 10 false 8 3 3 || COLLECTION_FAILURES=$((COLLECTION_FAILURES + 1))

echo '[collect] cpu-max-100'
run_scenario cpu-max-100 cpu/cpu-max-100 512 100 false 32 9 7 || COLLECTION_FAILURES=$((COLLECTION_FAILURES + 1))

echo '[collect] deadlock-multi-true'
run_scenario deadlock-multi-true deadlock/multi-true 512 10 true 16 0 6 || COLLECTION_FAILURES=$((COLLECTION_FAILURES + 1))

echo '[collect] deadlock-multi-false'
run_scenario deadlock-multi-false deadlock/multi-false 512 10 false 8 0 6 || COLLECTION_FAILURES=$((COLLECTION_FAILURES + 1))

echo '[collect] done'
printf 'scenario_collection_failures=%s\n' "$COLLECTION_FAILURES" > "$EVIDENCE_DIR/collection-status.txt"
[ "$COLLECTION_FAILURES" -eq 0 ]

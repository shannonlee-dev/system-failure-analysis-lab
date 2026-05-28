#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP="$ROOT_DIR/agent-app-leak/agent-app-leak"
EVIDENCE_DIR="$ROOT_DIR/evidence"
MONITOR="$ROOT_DIR/monitor.sh"
RUN_ROOT="/tmp/codyssey-real-evidence"
PORT="${AGENT_PORT:-15034}"

mkdir -p "$RUN_ROOT"

kill_tree() {
  local pid="$1"
  local child

  while read -r child; do
    [ -n "$child" ] || continue
    kill_tree "$child"
  done < <(pgrep -P "$pid" 2>/dev/null || true)

  kill "$pid" 2>/dev/null || true
}

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

  {
    printf -- '--- ps sample ---\n'
    ps -o pid,ppid,stat,pcpu,pmem,rss,comm,args -p "$pid" 2>/dev/null || true
    pgrep -P "$pid" 2>/dev/null | xargs -r ps -o pid,ppid,stat,pcpu,pmem,rss,comm,args -p 2>/dev/null || true
    printf -- '\n--- top sample ---\n'
    top -b -n 1 -p "$pid" 2>/dev/null | head -n 12 || true
    printf '\n'
  } >> "$out_file"
}

run_boot_failed() {
  local target="$EVIDENCE_DIR/boot-failed"
  local home="$RUN_ROOT/boot-failed-home"

  mkdir -p "$target" "$home/upload_files" "$home/api_keys" "$target"
  printf 'wrong_key\n' > "$home/api_keys/secret.key"
  chmod 600 "$home/api_keys/secret.key"

  : > "$target/stdout.log"
  : > "$target/stderr.log"

  set +e
  AGENT_HOME="$home" \
  AGENT_PORT="$PORT" \
  AGENT_UPLOAD_DIR="$home/upload_files" \
  AGENT_KEY_PATH="$home/api_keys" \
  AGENT_LOG_DIR="$target" \
  MEMORY_LIMIT=256 \
  CPU_MAX_OCCUPY=10 \
  MULTI_THREAD_ENABLE=false \
  "$APP" > "$target/stdout.log" 2> "$target/stderr.log"
  set -e
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
  wait_for_ready_or_exit "$pid" "$stdout_file" || true

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
    "$MONITOR" >> "$monitor_stdout" 2>&1 || true
    i=$((i + 1))
  done

  i=1
  while [ "$i" -le "$ps_count" ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
      break
    fi
    write_ps_top_sample "$pid" "$ps_top"
    sleep 1
    i=$((i + 1))
  done

  local waited=0
  while [ "$waited" -lt "$duration" ] && kill -0 "$pid" 2>/dev/null; do
    sleep 1
    waited=$((waited + 1))
  done

  if kill -0 "$pid" 2>/dev/null; then
    kill_tree "$pid"
  fi
  wait "$pid" 2>/dev/null || true
}

echo '[collect] boot-failed'
run_boot_failed

echo '[collect] boot-ready'
run_scenario boot-ready boot-ready 512 10 false 8 1 0

echo '[collect] scheduling-fcfs'
run_scenario scheduling-fcfs scheduling/priority 512 10 false 8 0 0

echo '[collect] oom-memory-50'
run_scenario oom-memory-50 oom/memory-50 50 10 false 8 3 3

echo '[collect] oom-memory-128'
run_scenario oom-memory-128 oom/memory-128 128 10 false 20 7 7

echo '[collect] cpu-max-10'
run_scenario cpu-max-10 cpu/cpu-max-10 512 10 false 8 3 3

echo '[collect] cpu-max-100'
run_scenario cpu-max-100 cpu/cpu-max-100 512 100 false 32 9 7

echo '[collect] deadlock-multi-true'
run_scenario deadlock-multi-true deadlock/multi-true 512 10 true 16 0 6

echo '[collect] deadlock-multi-false'
run_scenario deadlock-multi-false deadlock/multi-false 512 10 false 8 0 6

echo '[collect] done'

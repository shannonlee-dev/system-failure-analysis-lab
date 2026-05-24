#!/usr/bin/env bash
set -euo pipefail

APP_PATTERN="${AGENT_APP_PROCESS_NAME:-agent-app-leak}"
APP_PID="${AGENT_APP_PID:-}"
PORT="${AGENT_PORT:-15034}"

LOG_FILE="${MONITOR_LOG_FILE:-${AGENT_LOG_DIR:-/var/log/agent-app}/monitor.log}"
MAX_LOG_SIZE="${MONITOR_MAX_LOG_SIZE:-10485760}"
MAX_ROTATED_FILES="${MONITOR_MAX_ROTATED_FILES:-10}"
CPU_INTERVAL="${MONITOR_CPU_INTERVAL:-1}"

fail() {
  printf '%s\n' "$1"
  exit 1
}

warn_if_gt() {
  local label="$1"
  local value="$2"
  local threshold="$3"

  awk -v label="$label" -v value="$value" -v threshold="$threshold" '
    BEGIN {
      if ((value + 0) > (threshold + 0)) {
        printf("[WARNING] %s threshold exceeded (%s%% > %s%%)\n", label, value, threshold)
      }
    }'
}

unique_lines() {
  awk 'NF && !seen[$1]++ {print $1}'
}

get_child_pids_recursive() {
  local parent="$1"
  local child

  pgrep -P "$parent" 2>/dev/null | while read -r child; do
    printf '%s\n' "$child"
    get_child_pids_recursive "$child"
  done
}

find_app_pids() {
  if [ -n "$APP_PID" ]; then
    if ! ps -p "$APP_PID" >/dev/null 2>&1; then
      return 1
    fi

    {
      printf '%s\n' "$APP_PID"
      get_child_pids_recursive "$APP_PID"
    } | unique_lines

    return 0
  fi

  pgrep -u "$(id -u)" -f "$APP_PATTERN" 2>/dev/null \
    | awk -v self="$$" '$1 != self {print}' \
    | while read -r matched_pid; do
        printf '%s\n' "$matched_pid"
        get_child_pids_recursive "$matched_pid"
      done \
    | unique_lines
}

pick_primary_pid() {
  local best_pid=""
  local best_rss=-1
  local p
  local rss

  for p in $APP_PIDS; do
    [ -r "/proc/$p/status" ] || continue
    rss="$(awk '/^VmRSS:/ {print $2; exit}' "/proc/$p/status")"
    rss="${rss:-0}"

    if [ "$rss" -gt "$best_rss" ]; then
      best_rss="$rss"
      best_pid="$p"
    fi
  done

  if [ -n "$best_pid" ]; then
    printf '%s\n' "$best_pid"
  else
    printf '%s\n' "$APP_PIDS" | head -n 1
  fi
}

read_total_jiffies() {
  awk '/^cpu / {
    total = 0
    for (i = 2; i <= NF; i++) {
      total += $i
    }
    print total
  }' /proc/stat
}

read_one_thread_jiffies() {
  local stat_file="$1"

  awk '
    {
      line = $0
      sub(/^[0-9]+ \([^)]*\) /, "", line)
      split(line, f, " ")

      # after removing "pid (comm) ":
      # f[1]=state
      # f[12]=utime
      # f[13]=stime
      print f[12] + f[13]
    }
  ' "$stat_file" 2>/dev/null || printf '0\n'
}

read_app_jiffies_sum() {
  local total=0
  local p
  local task_stat
  local value

  for p in $APP_PIDS; do
    [ -d "/proc/$p/task" ] || continue

    for task_stat in /proc/"$p"/task/*/stat; do
      [ -r "$task_stat" ] || continue
      value="$(read_one_thread_jiffies "$task_stat")"
      value="${value:-0}"
      total=$((total + value))
    done
  done

  printf '%s\n' "$total"
}

sample_cpu_percent() {
  if [ -n "${MONITOR_CPU_OVERRIDE:-}" ]; then
    printf '%s\n' "$MONITOR_CPU_OVERRIDE"
    return 0
  fi

  local app1
  local app2
  local total1
  local total2

  app1="$(read_app_jiffies_sum)"
  total1="$(read_total_jiffies)"

  sleep "$CPU_INTERVAL"

  app2="$(read_app_jiffies_sum)"
  total2="$(read_total_jiffies)"

  awk -v a1="$app1" -v a2="$app2" -v t1="$total1" -v t2="$total2" '
    BEGIN {
      app_delta = a2 - a1
      total_delta = t2 - t1

      if (total_delta <= 0 || app_delta < 0) {
        printf "0.00"
      } else {
        printf "%.2f", (app_delta / total_delta) * 100
      }
    }'
}

sample_rss_kb_sum() {
  if [ -n "${MONITOR_MEM_KB_OVERRIDE:-}" ]; then
    printf '%s\n' "$MONITOR_MEM_KB_OVERRIDE"
    return 0
  fi

  local total=0
  local p
  local rss

  for p in $APP_PIDS; do
    [ -r "/proc/$p/status" ] || continue
    rss="$(awk '/^VmRSS:/ {print $2; exit}' "/proc/$p/status")"
    rss="${rss:-0}"
    total=$((total + rss))
  done

  printf '%s\n' "$total"
}

sample_mem_mb() {
  if [ -n "${MONITOR_MEM_MB_OVERRIDE:-}" ]; then
    printf '%s\n' "$MONITOR_MEM_MB_OVERRIDE"
    return 0
  fi

  local rss_kb="$1"

  awk -v kb="$rss_kb" 'BEGIN {
    printf "%.1f", kb / 1024
  }'
}

sample_mem_percent() {
  if [ -n "${MONITOR_MEM_OVERRIDE:-}" ]; then
    printf '%s\n' "$MONITOR_MEM_OVERRIDE"
    return 0
  fi

  local rss_kb="$1"
  local mem_total_kb

  mem_total_kb="$(awk '/^MemTotal:/ {print $2; exit}' /proc/meminfo)"

  awk -v rss="$rss_kb" -v total="$mem_total_kb" 'BEGIN {
    if (total <= 0) {
      printf "0.0"
    } else {
      printf "%.1f", (rss / total) * 100
    }
  }'
}

sample_disk_percent() {
  if [ -n "${MONITOR_DISK_OVERRIDE:-}" ]; then
    printf '%s\n' "$MONITOR_DISK_OVERRIDE"
    return 0
  fi

  df / | awk 'NR == 2 {gsub("%", "", $5); print $5}'
}

rotate_logs_if_needed() {
  [ -f "$LOG_FILE" ] || return 0

  local current_size
  local i

  current_size="$(stat -c '%s' "$LOG_FILE" 2>/dev/null || printf '0')"
  [ "$current_size" -le "$MAX_LOG_SIZE" ] && return 0

  i=$((MAX_ROTATED_FILES - 1))
  while [ "$i" -ge 1 ]; do
    if [ -f "$LOG_FILE.$i" ]; then
      mv "$LOG_FILE.$i" "$LOG_FILE.$((i + 1))"
    fi
    i=$((i - 1))
  done

  mv "$LOG_FILE" "$LOG_FILE.1"
  : > "$LOG_FILE"

  find "$(dirname "$LOG_FILE")" -maxdepth 1 -type f -name "$(basename "$LOG_FILE").*" \
    | sort -Vr \
    | awk -v keep="$MAX_ROTATED_FILES" 'NR > keep {print}' \
    | xargs -r rm -f
}

check_port() {
  ss -tuln | awk -v port=":$PORT" '
    $5 ~ port "$" {
      found = 1
    }
    END {
      exit found ? 0 : 1
    }'
}

check_firewall() {
  # 1) sudo 없이 ufw status 시도
  if command -v ufw >/dev/null 2>&1; then
    firewall_output="$(ufw status 2>/dev/null || true)"
    firewall_status="$(printf '%s\n' "$firewall_output" | awk -F': ' '/^Status:/ {print $2; exit}')"

    if [ "$firewall_status" = "active" ]; then
      printf '%s\n' '[OK] firewall is active'
      return 0
    fi

    # 2) sudo -n: 비밀번호 없이 sudo 가능한 경우만 시도
    if command -v sudo >/dev/null 2>&1; then
      firewall_output="$(sudo -n ufw status 2>/dev/null || true)"
      firewall_status="$(printf '%s\n' "$firewall_output" | awk -F': ' '/^Status:/ {print $2; exit}')"

      if [ "$firewall_status" = "active" ]; then
        printf '%s\n' '[OK] firewall is active'
        return 0
      fi
    fi

    printf '%s\n' '[WARNING] firewall status is not active or not readable by current user'
    return 0
  fi

  if command -v firewall-cmd >/dev/null 2>&1; then
    firewall_state="$(firewall-cmd --state 2>/dev/null || true)"

    if [ "$firewall_state" = "running" ]; then
      printf '%s\n' '[OK] firewall is active'
    else
      printf '%s\n' '[WARNING] firewall is not active or not readable by current user'
    fi
    return 0
  fi

  printf '%s\n' '[WARNING] firewall command is not available'
  return 0
}

print_debug() {
  local rss_kb="$1"
  local mem_total_kb
  local pid_list

  [ "${MONITOR_DEBUG:-0}" = "1" ] || return 0

  mem_total_kb="$(awk '/^MemTotal:/ {print $2; exit}' /proc/meminfo)"
  pid_list="$(printf '%s\n' "$APP_PIDS" | paste -sd, -)"

  printf '\n[DEBUG]\n'
  printf 'Matched PIDs : %s\n' "$pid_list"
  printf 'Primary PID  : %s\n' "$PRIMARY_PID"
  printf 'VmRSS Sum    : %s kB\n' "$rss_kb"
  printf 'MemTotal     : %s kB\n' "$mem_total_kb"
  printf 'CPU Interval : %ss\n' "$CPU_INTERVAL"
}

printf '%s\n' '====== SYSTEM MONITOR RESULT ======'
printf '\n%s\n' '[HEALTH CHECK]'

APP_PIDS="$(find_app_pids || true)"
if [ -z "$APP_PIDS" ]; then
  fail "Checking process '$APP_PATTERN'... [FAIL]"
fi

PRIMARY_PID="$(pick_primary_pid)"
PID_LIST="$(printf '%s\n' "$APP_PIDS" | paste -sd, -)"

printf "Checking process '%s'... [OK] (PID: %s)\n" "$APP_PATTERN" "$PRIMARY_PID"
printf "Tracking process tree... [OK] (PIDS: %s)\n" "$PID_LIST"

if ! check_port; then
  fail "Checking port $PORT... [FAIL]"
fi
printf 'Checking port %s... [OK]\n' "$PORT"

check_firewall

printf '\n%s\n' '[RESOURCE MONITORING]'

cpu="$(sample_cpu_percent)"
rss_kb="$(sample_rss_kb_sum)"
mem="$(sample_mem_percent "$rss_kb")"
mem_mb="$(sample_mem_mb "$rss_kb")"
disk="$(sample_disk_percent)"

printf 'CPU Usage : %s%%\n' "$cpu"
printf 'MEM Usage : %s%%\n' "$mem"
printf 'MEM RSS   : %sMB\n' "$mem_mb"
printf 'DISK Used : %s%%\n' "$disk"

print_debug "$rss_kb"

warn_if_gt "CPU" "$cpu" "20"
warn_if_gt "MEM" "$mem" "10"
warn_if_gt "DISK_USED" "$disk" "80"

log_dir="$(dirname "$LOG_FILE")"

if [ ! -d "$log_dir" ]; then
  fail "Log directory does not exist: $log_dir"
fi

if [ ! -w "$log_dir" ]; then
  fail "Log directory is not writable: $log_dir"
fi

rotate_logs_if_needed

printf '[%s] PID:%s CPU:%s%% MEM:%s%% RSS_MB:%s DISK_USED:%s%%\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$PRIMARY_PID" \
  "$cpu" \
  "$mem" \
  "$mem_mb" \
  "$disk" >> "$LOG_FILE" \
  || fail "Failed to append log: $LOG_FILE"

printf '\n[INFO] Log appended: %s\n' "$LOG_FILE"
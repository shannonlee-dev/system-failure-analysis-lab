# 98_PROCEDURE_MANUAL

## 1. 작업 기록 폴더 만들기

1. 홈 폴더에 미션 작업 폴더를 만든다.

복붙 명령어:
~~~sh
mkdir -p "$HOME/agent-troubleshooting/reports" "$HOME/agent-troubleshooting/logs" "$HOME/agent-troubleshooting/screenshots"
cd "$HOME/agent-troubleshooting"
pwd
~~~

예상 화면/출력:
~~~text
/home/<현재사용자이름>/agent-troubleshooting
~~~

## 2. 기본 환경 확인하기

1. root 사용자가 아닌지 확인한다.

복붙 명령어:
~~~sh
id -un
test "$(id -u)" -ne 0 && echo "일반 사용자입니다"
~~~

예상 화면/출력:
~~~text
<현재사용자이름>
일반 사용자입니다
~~~

2. 리눅스 명령어가 있는지 확인한다.

복붙 명령어:
~~~sh
command -v ps
command -v top
command -v kill
command -v tee
~~~

예상 화면/출력:
~~~text
/usr/bin/ps
/usr/bin/top
/usr/bin/kill
/usr/bin/tee
~~~

## 3. 필요한 프로그램 설치하기

1. 화면 캡처와 프로세스 확인 도구가 필요하면 설치한다.

복붙 명령어:
~~~sh
sudo apt update
sudo apt install -y htop psmisc
~~~

예상 화면/출력:
~~~text
패키지 목록을 읽는 중...
htop, psmisc 설치 또는 이미 설치됨
~~~

## 4. 미션에서 사용할 값 정하기

1. 앱 실행에 사용할 기본 폴더와 환경변수를 준비한다.

복붙 명령어:
~~~sh
mkdir -p "$HOME/agent-app/upload_files" "$HOME/agent-app/api_keys" "$HOME/agent-app/logs"
printf 'agent_api_key_test\n' > "$HOME/agent-app/api_keys/secret.key"
chmod 600 "$HOME/agent-app/api_keys/secret.key"
cat > "$HOME/agent-troubleshooting/env-default.sh" <<'EOF'
export AGENT_HOME="$HOME/agent-app"
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR="$AGENT_HOME/upload_files"
export AGENT_KEY_PATH="$AGENT_HOME/api_keys"
export AGENT_LOG_DIR="$AGENT_HOME/logs"
export MEMORY_LIMIT=256
export CPU_MAX_OCCUPY=10
export MULTI_THREAD_ENABLE=false
EOF
~~~

예상 화면/출력:
~~~text
명령이 끝나고 오류가 없으면 다음 단계로 진행
~~~

2. 제공받은 앱 파일을 작업 폴더에 둔다.

복붙 명령어:
~~~sh
cp <agent-app-leak_파일경로> "$HOME/agent-troubleshooting/agent-app-leak"

cat << 'EOF' > monitor.sh
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
  if command -v ufw >/dev/null 2>&1; then
    firewall_output="$(ufw status 2>/dev/null || true)"
    firewall_status="$(printf '%s\n' "$firewall_output" | awk -F': ' '/^Status:/ {print $2; exit}')"

    if [ "$firewall_status" = "active" ]; then
      printf '%s\n' '[OK] firewall is active'
      return 0
    fi

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
EOF

chmod +x monitor.sh

chmod u+x "$HOME/agent-troubleshooting/agent-app-leak" "$HOME/agent-troubleshooting/monitor.sh"
ls -l "$HOME/agent-troubleshooting/agent-app-leak" "$HOME/agent-troubleshooting/monitor.sh"
~~~

예상 화면/출력:
~~~text
-rwx... agent-app-leak
-rwx... monitor.sh
~~~

## 5. 단계별 복붙 절차

1. 기본 환경으로 앱을 실행하고 로그를 저장한다.

복붙 명령어:
~~~sh
cd "$HOME/agent-troubleshooting"
. ./env-default.sh
./agent-app-leak 2>&1 | tee "logs/app-default.log"
~~~

예상 화면/출력:
~~~text
앱 시작 로그와 진행 로그가 표시됨
~~~

2. 다른 터미널에서 관제 로그를 저장한다.

복붙 명령어:
~~~sh
cd "$HOME/agent-troubleshooting"
./monitor.sh 2>&1 | tee "logs/monitor-default.log"
~~~

예상 화면/출력:
~~~text
PROCESS:agent-app-leak CPU:<수치>% MEM:<수치>% ...
~~~

3. OOM 분석용으로 메모리 제한을 바꾸어 두 번 비교 실행한다.

복붙 명령어:
~~~sh
cd "$HOME/agent-troubleshooting"
. ./env-default.sh
MEMORY_LIMIT=50 CPU_MAX_OCCUPY=100 MULTI_THREAD_ENABLE=false ./agent-app-leak 2>&1 | tee "logs/oom-memory-50.log"
MEMORY_LIMIT=128 CPU_MAX_OCCUPY=100 MULTI_THREAD_ENABLE=false ./agent-app-leak 2>&1 | tee "logs/oom-memory-128.log"
~~~

예상 화면/출력:
~~~text
각 실행 로그에 MemoryGuard와 Self-terminating 메시지, 생존 시간 차이가 기록됨
~~~

4. CPU 분석용으로 CPU 제한을 바꾸어 비교 실행한다.

복붙 명령어:
~~~sh
cd "$HOME/agent-troubleshooting"
. ./env-default.sh
MEMORY_LIMIT=512 MULTI_THREAD_ENABLE=false CPU_MAX_OCCUPY=10 ./agent-app-leak 2>&1 | tee "logs/cpu-max-10.log"
MEMORY_LIMIT=512 MULTI_THREAD_ENABLE=false CPU_MAX_OCCUPY=100 ./agent-app-leak 2>&1 | tee "logs/cpu-max-100.log"
~~~

예상 화면/출력:
~~~text
10 조건에서는 Peak reached와 cooldown 로그가 보이고, 100 조건에서는 CPU Threshold Violated 로그가 보임
~~~

5. CPU 사용률이 올라가는 순간을 확인한다.

복붙 명령어:
~~~sh
ps -eo pid,comm,pcpu,pmem,args | grep '[a]gent-app-leak'
top -b -n 1 -w 200 | grep 'agent-app-leak'
~~~

예상 화면/출력:
~~~text
agent-app-leak 프로세스의 PID, CPU%, MEM%가 표시됨
~~~

6. Deadlock 분석용으로 멀티스레드 설정을 바꾸어 비교 실행한다.

복붙 명령어:
~~~sh
cd "$HOME/agent-troubleshooting"
. ./env-default.sh
MEMORY_LIMIT=512 CPU_MAX_OCCUPY=10 MULTI_THREAD_ENABLE=true ./agent-app-leak 2>&1 | tee "logs/deadlock-multi-true.log"
MEMORY_LIMIT=512 CPU_MAX_OCCUPY=10 MULTI_THREAD_ENABLE=false ./agent-app-leak 2>&1 | tee "logs/deadlock-multi-false.log"
~~~

예상 화면/출력:
~~~text
true 실행에서는 WAITING/BLOCKED 로그와 멈춤 상태가 보이고, false 실행에서는 회피 결과가 기록됨
~~~

7. 멈춘 프로세스와 스레드 상태를 확인한다.

복붙 명령어:
~~~sh
ps -ef | grep '[a]gent-app-leak'
ps -L -p <PID번호> -o pid,tid,stat,pcpu,pmem,comm
top -H -b -n 1 -p <PID번호>
~~~

예상 화면/출력:
~~~text
PID와 스레드 목록이 보이고 CPU/MEM 변화가 거의 없는지 확인할 수 있음
~~~

## 6. 로그와 출력 기록하기

1. OOM 리포트 초안을 만든다.

복붙 명령어:
~~~sh
cat > "$HOME/agent-troubleshooting/reports/oom.md" <<'EOF'
[Bug] OOM Crash - <한 줄 요약>

## 1. Description (현상 설명)
- 

## 2. Evidence & Logs (증거 자료)
- monitor.sh 관제 로그:
- 프로그램 실행 로그:
- ps/top 출력:

## 3. Root Cause Analysis (원인 분석)
- 

## 4. Workaround & Verification (조치 및 검증)
- MEMORY_LIMIT 변경 전:
- MEMORY_LIMIT 변경 후:
EOF
~~~

예상 화면/출력:
~~~text
reports/oom.md 파일이 만들어짐
~~~

2. CPU 리포트 초안을 만든다.

복붙 명령어:
~~~sh
cat > "$HOME/agent-troubleshooting/reports/cpu.md" <<'EOF'
[Bug] CPU Latency - <한 줄 요약>

## 1. Description (현상 설명)
- 

## 2. Evidence & Logs (증거 자료)
- monitor.sh 관제 로그:
- CPU Threshold 실행 로그:
- ps/top 출력:

## 3. Root Cause Analysis (원인 분석)
- 

## 4. Workaround & Verification (조치 및 검증)
- CPU_MAX_OCCUPY 변경 전:
- CPU_MAX_OCCUPY 변경 후:
EOF
~~~

예상 화면/출력:
~~~text
reports/cpu.md 파일이 만들어짐
~~~

3. Deadlock 리포트 초안을 만든다.

복붙 명령어:
~~~sh
cat > "$HOME/agent-troubleshooting/reports/deadlock.md" <<'EOF'
[Bug] Deadlock - <한 줄 요약>

## 1. Description (현상 설명)
- 

## 2. Evidence & Logs (증거 자료)
- PID 존재 증거:
- CPU/MEM 정체 증거:
- 마지막 WAITING/BLOCKED 로그:

## 3. Root Cause Analysis (원인 분석)
- 

## 4. Workaround & Verification (조치 및 검증)
- MULTI_THREAD_ENABLE=true:
- MULTI_THREAD_ENABLE=false:
EOF
~~~

예상 화면/출력:
~~~text
reports/deadlock.md 파일이 만들어짐
~~~

## 7. 최종 산출물 확인하기

1. 리포트 3개가 있는지 확인한다.

복붙 명령어:
~~~sh
ls -l "$HOME/agent-troubleshooting/reports/oom.md" \
      "$HOME/agent-troubleshooting/reports/cpu.md" \
      "$HOME/agent-troubleshooting/reports/deadlock.md"
~~~

예상 화면/출력:
~~~text
oom.md, cpu.md, deadlock.md 파일 3개가 표시됨
~~~

2. 각 리포트에 4개 섹션이 있는지 확인한다.

복붙 명령어:
~~~sh
grep -R "^## 1\\. Description\\|^## 2\\. Evidence & Logs\\|^## 3\\. Root Cause Analysis\\|^## 4\\. Workaround & Verification" "$HOME/agent-troubleshooting/reports"
~~~

예상 화면/출력:
~~~text
각 리포트마다 Description, Evidence & Logs, Root Cause Analysis, Workaround & Verification 줄이 표시됨
~~~

3. 제출용 PDF가 필요하면 리포트를 하나로 묶는다.

복붙 명령어:
~~~sh
cd "$HOME/agent-troubleshooting"
cat reports/oom.md reports/cpu.md reports/deadlock.md > reports/final-report.md
ls -l reports/final-report.md
~~~

예상 화면/출력:
~~~text
reports/final-report.md 파일이 표시됨
~~~

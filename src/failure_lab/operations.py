"""환경 편집·수집·CPU 분석·문법 검사 명령."""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

from .config import agent_port, env_value, read_env_lines, replace_env_value
from .constant import COLLECT, CONFIG, CPU_SAMPLER, ENV_KEYS, MONITOR, ROOT
from .process import pids_listening_on_port
from .runner import run, run_shell
from .ui import S, header, pause


def edit_env(*, interactive: bool = True) -> int:
    if interactive:
        header()
    print(S.title("환경값 수정"))
    if not CONFIG.exists():
        print(S.bad(f"누락된 파일: {CONFIG.relative_to(ROOT)}"))
        pause(interactive)
        return 1
    if not sys.stdin.isatty():
        print("환경값 수정은 인터랙티브 모드에서 실행하세요.")
        return 2

    lines = read_env_lines()
    for index, key in enumerate(ENV_KEYS, 1):
        print(f"{index}. {key:<20} {env_value(lines, key)}")
    print("0. 취소")

    choice = input("\n수정할 번호: ").strip()
    if choice == "0":
        print("취소했습니다.")
        pause(interactive)
        return 0
    if not choice.isdigit() or not (1 <= int(choice) <= len(ENV_KEYS)):
        print(S.bad("없는 번호입니다."))
        pause(interactive)
        return 2

    key = ENV_KEYS[int(choice) - 1]
    current = env_value(lines, key)
    new_value = input(f"{key} 새 값 [{current}]: ").strip()
    if not new_value:
        print("변경하지 않았습니다.")
        pause(interactive)
        return 0

    CONFIG.write_text("\n".join(replace_env_value(lines, key, new_value)) + "\n")
    print(S.ok(f"수정 완료: {key}={new_value}"))
    pause(interactive)
    return 0


def run_monitor(*, interactive: bool = True) -> int:
    if interactive:
        header()
    print(S.title("모니터 실행"))
    code = run_shell(
        f"source {shlex.quote(str(CONFIG))} && {shlex.quote(str(MONITOR))}"
    )
    pause(interactive)
    return code


def collect_evidence(*, interactive: bool = True, output: Path | None = None) -> int:
    if interactive:
        header()
    print(S.title("증거 재수집"))
    command = [str(COLLECT)]
    if output is not None:
        command.extend(["--output", str(output)])
    code = run(command)
    pause(interactive)
    return code


def sample_cpu(*, interactive: bool = True, output: Path | None = None) -> int:
    if interactive:
        header()
    print(S.title("CPU 샘플링"))
    if not CPU_SAMPLER.exists():
        print(S.bad(f"누락된 파일: {CPU_SAMPLER.relative_to(ROOT)}"))
        pause(interactive)
        return 1
    port = agent_port()
    if not pids_listening_on_port(port):
        print(
            S.warn(
                f"포트 {port}에서 실행 중인 앱을 찾지 못했습니다. 먼저 앱을 시작하세요."
            )
        )
        pause(interactive)
        return 1

    duration = os.environ.get("DURATION", "30")
    interval = os.environ.get("INTERVAL", "0.1")
    if interactive and sys.stdin.isatty():
        next_duration = input(f"샘플링 시간(초) [{duration}]: ").strip()
        next_interval = input(f"샘플 간격(초) [{interval}]: ").strip()
        duration = next_duration or duration
        interval = next_interval or interval

    command = (
        f"source {shlex.quote(str(CONFIG))} && "
        f"DURATION={shlex.quote(duration)} INTERVAL={shlex.quote(interval)} "
        f"{shlex.quote(str(CPU_SAMPLER))}"
    )
    if output is not None:
        command += f" --output {shlex.quote(str(output))}"
    code = run_shell(command)
    pause(interactive)
    return code


def analyze_cpu(*, interactive: bool = True) -> int:
    if interactive:
        header()
    print(S.title("CPU 급상승 분석"))
    code = run([sys.executable, "-m", "failure_lab.cpu_spike"])
    pause(interactive)
    return code


def syntax_check(*, interactive: bool = True) -> int:
    if interactive:
        header()
    print(S.title("문법 검사"))
    python_check = (
        "import ast, pathlib, sys; "
        "[ast.parse(pathlib.Path(p).read_text(), filename=p) for p in sys.argv[1:]]"
    )
    python_files = sorted((ROOT / "src" / "failure_lab").rglob("*.py"))
    checks = [
        ["bash", "-n", str(MONITOR)],
        ["bash", "-n", str(COLLECT)],
        ["bash", "-n", str(CPU_SAMPLER)],
        [sys.executable, "-B", "-c", python_check, *map(str, python_files)],
    ]
    ok = True
    for command in checks:
        code = run(command)
        ok = ok and code == 0
    pause(interactive)
    return 0 if ok else 1

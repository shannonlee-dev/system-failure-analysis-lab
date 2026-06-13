from __future__ import annotations

import argparse
import os
import shlex
import sys

from .app import STARTED_PIDS, start_app, stop_app
from .config import agent_port, env_value, read_env_lines, replace_env_value
from .constant import COLLECT, CONFIG, CPU_ANALYZER, CPU_SAMPLER, ENV_KEYS, MONITOR, ROOT
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
    code = run_shell(f"source {shlex.quote(str(CONFIG))} && {shlex.quote(str(MONITOR))}")
    pause(interactive)
    return code


def collect_evidence(*, interactive: bool = True) -> int:
    if interactive:
        header()
    print(S.title("증거 재수집"))
    code = run([str(COLLECT)])
    pause(interactive)
    return code


def sample_cpu(*, interactive: bool = True) -> int:
    if interactive:
        header()
    print(S.title("CPU 샘플링"))
    if not CPU_SAMPLER.exists():
        print(S.bad(f"누락된 파일: {CPU_SAMPLER.relative_to(ROOT)}"))
        pause(interactive)
        return 1
    port = agent_port()
    if not pids_listening_on_port(port):
        print(S.warn(f"포트 {port}에서 실행 중인 앱을 찾지 못했습니다. 먼저 앱을 시작하세요."))
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
    code = run_shell(command)
    pause(interactive)
    return code


def analyze_cpu(*, interactive: bool = True) -> int:
    if interactive:
        header()
    print(S.title("CPU 급상승 분석"))
    code = run([sys.executable, str(CPU_ANALYZER)])
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
    python_files = [
        ROOT / "main.py",
        ROOT / "lab" / "app.py",
        ROOT / "lab" / "cli.py",
        ROOT / "lab" / "commands.py",
        ROOT / "lab" / "config.py",
        ROOT / "lab" / "constant.py",
        ROOT / "lab" / "process.py",
        ROOT / "lab" / "runner.py",
        ROOT / "lab" / "ui.py",
        CPU_ANALYZER,
        ROOT / "tools" / "cpu_spike" / "analysis.py",
        ROOT / "tools" / "cpu_spike" / "cli.py",
        ROOT / "tools" / "cpu_spike" / "io.py",
        ROOT / "tools" / "cpu_spike" / "model.py",
        ROOT / "tools" / "cpu_spike" / "plot.py",
        ROOT / "tools" / "cpu_spike" / "report.py",
        ROOT / "tools" / "__init__.py",
        ROOT / "tools" / "cpu_spike" / "__init__.py",
    ]
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="장애 분석 랩 CLI. 인자 없이 실행하면 메뉴 모드가 열립니다.")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("start", help="기본 환경으로 대상 앱 실행")
    sub.add_parser("stop", help="대상 앱 종료 및 AGENT_PORT 비우기")
    sub.add_parser("edit-env", help="config/env-default.sh 대화형 수정")
    sub.add_parser("monitor", help="기본 환경으로 monitor.sh 실행")
    sub.add_parser("sample-cpu", help="tools/monitor_cpu_sampling.sh 실행")
    sub.add_parser("collect", help="시나리오 증거 재수집")
    sub.add_parser("analyze-cpu", help="CPU 급상승 분석 실행")
    sub.add_parser("check", help="문법 검사 실행")
    return parser


def dispatch(command: str | None) -> int:
    actions = {
        "start": start_app,
        "stop": stop_app,
        "edit-env": edit_env,
        "monitor": run_monitor,
        "sample-cpu": sample_cpu,
        "collect": collect_evidence,
        "analyze-cpu": analyze_cpu,
        "check": syntax_check,
    }
    if command in actions:
        return actions[command](interactive=False)
    return 2


def menu() -> int:
    actions = {
        "1": ("앱 시작", start_app),
        "2": ("앱 종료 / 포트 비우기", stop_app),
        "3": ("환경값 수정", edit_env),
        "4": ("모니터 실행", run_monitor),
        "5": ("CPU 샘플링 실행", sample_cpu),
        "6": ("CPU 급상승 분석", analyze_cpu),
        "7": ("증거 재수집", collect_evidence),
        "8": ("스크립트 문법 검사", syntax_check),
    }
    try:
        while True:
            header()
            for key, (label, _) in actions.items():
                print(f"{key}. {label}")
            print("0. 종료")
            choice = input("\n번호 선택: ").strip()
            if choice == "0":
                print("좋습니다. 작업을 마칩니다.")
                return 0
            action = actions.get(choice)
            if action is None:
                print(S.bad("없는 번호입니다."))
                pause(True)
                continue
            action[1](interactive=True)
    finally:
        if STARTED_PIDS:
            stop_app(interactive=False, force_port=True)


def main() -> int:
    try:
        parser = build_parser()
        if len(sys.argv) == 1:
            return menu()
        args = parser.parse_args()
        return dispatch(args.command)
    except KeyboardInterrupt:
        print("\n중단했습니다.")
        return 130

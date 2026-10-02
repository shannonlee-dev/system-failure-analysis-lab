"""인자 파싱·명령 분기·CLI 진입점."""

from __future__ import annotations

import argparse
import sys

from .app import start_app, stop_app
from .menu import menu
from .operations import (
    analyze_cpu,
    collect_evidence,
    edit_env,
    run_monitor,
    sample_cpu,
    syntax_check,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="failure-lab",
        description="장애 분석 랩 CLI. 인자 없이 실행하면 메뉴 모드가 열립니다.",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("start", help="기본 환경으로 대상 앱 실행")
    sub.add_parser("stop", help="대상 앱 종료 및 AGENT_PORT 비우기")
    sub.add_parser("edit-env", help="config/env-default.sh 대화형 수정")
    sub.add_parser("monitor", help="기본 환경으로 monitor.sh 실행")
    sub.add_parser("sample-cpu", help="scripts/monitor_cpu_sampling.sh 실행")
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

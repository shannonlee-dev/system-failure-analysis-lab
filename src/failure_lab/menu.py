"""대화형 실험 메뉴와 종료 정리."""

from __future__ import annotations

from .app import STARTED_PIDS, start_app, stop_app
from .operations import (
    analyze_cpu,
    collect_evidence,
    edit_env,
    run_monitor,
    sample_cpu,
    syntax_check,
)
from .ui import S, header, pause


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

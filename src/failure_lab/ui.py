from __future__ import annotations

import os
import sys

from .constant import ROOT


class Style:
    def __init__(self) -> None:
        self.enabled = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    def c(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text

    def title(self, text: str) -> str:
        return self.c("1;36", text)

    def ok(self, text: str) -> str:
        return self.c("32", text)

    def warn(self, text: str) -> str:
        return self.c("33", text)

    def bad(self, text: str) -> str:
        return self.c("31", text)

    def dim(self, text: str) -> str:
        return self.c("2", text)


S = Style()


def header() -> None:
    if sys.stdout.isatty():
        os.system("clear")
    print(S.title("시스템 장애 분석 랩"))
    print("장애 증거, 모니터 출력, 분석 리포트를 한 곳에서 다룹니다.")
    print(S.dim("인자 모드도 지원합니다: uv run failure-lab --help"))
    print(S.dim(f"저장소: {ROOT}"))
    print()


def pause(interactive: bool) -> None:
    if interactive:
        input(S.dim("\nEnter를 누르면 메뉴로 돌아갑니다. "))

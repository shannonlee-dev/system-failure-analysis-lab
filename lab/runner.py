from __future__ import annotations

import shlex
import subprocess

from .constant import ROOT
from .ui import S


def run(command: list[str]) -> int:
    print(S.dim("$ " + " ".join(shlex.quote(part) for part in command)))
    try:
        return subprocess.run(command, cwd=str(ROOT), check=False).returncode
    except FileNotFoundError:
        print(S.bad(f"명령을 찾을 수 없습니다: {command[0]}"))
        return 127


def run_shell(command: str) -> int:
    print(S.dim(f"$ {command}"))
    return subprocess.run(["bash", "-lc", command], cwd=str(ROOT), check=False).returncode


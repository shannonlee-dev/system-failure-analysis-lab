from __future__ import annotations

import os
import platform
import shlex
import subprocess
import time
import zipfile

from .config import agent_port
from .constant import APP, APP_ZIP, CONFIG, INTERACTIVE_LOG_DIR, ROOT
from .process import agent_process_pids, pids_listening_on_port, terminate_pids
from .runner import run_shell
from .ui import S, header, pause

STARTED_PIDS: set[int] = set()


def stop_app(*, interactive: bool = True, force_port: bool = True) -> int:
    if interactive:
        header()
    print(S.title("앱 종료 / 포트 비우기"))
    port = agent_port()
    targets = set(STARTED_PIDS)
    targets.update(agent_process_pids())
    if force_port:
        targets.update(pids_listening_on_port(port))
    killed = terminate_pids(targets)
    STARTED_PIDS.difference_update(killed)
    remaining = pids_listening_on_port(port)
    if remaining:
        print(
            S.warn(
                f"포트 {port} 리스너가 남아 있습니다: {', '.join(map(str, sorted(remaining)))}"
            )
        )
        pause(interactive)
        return 1
    if killed:
        print(S.ok(f"종료 완료: {', '.join(map(str, sorted(killed)))}"))
    else:
        print(S.ok(f"실행 중인 앱이 없고 포트 {port}도 비어 있습니다."))
    pause(interactive)
    return 0


def ensure_app() -> bool:
    if APP.exists() and os.access(APP, os.X_OK):
        return True
    if not APP_ZIP.exists():
        print(S.bad(f"누락된 파일: {APP_ZIP.relative_to(ROOT)}"))
        return False

    machine = platform.machine().lower()
    member = (
        "agent-leak-app-arm64"
        if machine in {"aarch64", "arm64"}
        else "agent-leak-app-x86"
    )
    try:
        with zipfile.ZipFile(APP_ZIP) as zf:
            data = zf.read(member)
    except (KeyError, zipfile.BadZipFile) as exc:
        print(S.bad(f"압축 파일에서 앱을 꺼낼 수 없습니다: {exc}"))
        return False

    APP.write_bytes(data)
    APP.chmod(0o750)
    print(S.ok(f"대상 앱 추출 완료: {APP.relative_to(ROOT)}"))
    return True


def start_app(*, interactive: bool = True) -> int:
    if interactive:
        header()
    print(S.title("앱 시작"))
    if not CONFIG.exists():
        print(S.bad(f"누락된 파일: {CONFIG.relative_to(ROOT)}"))
        pause(interactive)
        return 1
    if not ensure_app():
        pause(interactive)
        return 1

    port = agent_port()
    if pids_listening_on_port(port):
        print(S.warn(f"포트 {port}가 사용 중입니다. 기존 앱/리스너를 먼저 정리합니다."))
        stop_app(interactive=False, force_port=True)

    command = f"""
source {shlex.quote(str(CONFIG))}
mkdir -p "$AGENT_UPLOAD_DIR" "$AGENT_KEY_PATH" "$AGENT_LOG_DIR"
if [ ! -f "$AGENT_KEY_PATH/secret.key" ]; then
  printf '%s\\n' 'agent_api_key_test' > "$AGENT_KEY_PATH/secret.key"
  chmod 600 "$AGENT_KEY_PATH/secret.key"
fi
exec {shlex.quote(str(APP))}
""".strip()
    if not interactive:
        print(S.dim("종료하려면 Ctrl-C를 누르세요."))
        try:
            code = run_shell(command)
        finally:
            stop_app(interactive=False, force_port=True)
        return code

    print(S.dim("$ " + shlex.join(["bash", "-lc", command])))
    INTERACTIVE_LOG_DIR.mkdir(parents=True, exist_ok=True)
    stdout_path = INTERACTIVE_LOG_DIR / "agent_app.stdout.log"
    stderr_path = INTERACTIVE_LOG_DIR / "agent_app.stderr.log"
    stdout_file = stdout_path.open("ab")
    stderr_file = stderr_path.open("ab")
    try:
        proc = subprocess.Popen(
            ["bash", "-lc", command],
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=True,
        )
    finally:
        stdout_file.close()
        stderr_file.close()
    STARTED_PIDS.add(proc.pid)
    deadline = time.time() + 8
    while time.time() < deadline and proc.poll() is None:
        listeners = pids_listening_on_port(port)
        if listeners:
            STARTED_PIDS.update(listeners)
            print(
                S.ok(
                    f"앱 실행 중: PID {', '.join(map(str, sorted(listeners)))}, port {port}"
                )
            )
            pause(interactive)
            return 0
        time.sleep(0.2)
    if proc.poll() is not None:
        STARTED_PIDS.discard(proc.pid)
        print(S.bad(f"앱이 바로 종료되었습니다. exit={proc.returncode}"))
        print(S.dim(f"stdout: {stdout_path.relative_to(ROOT)}"))
        print(S.dim(f"stderr: {stderr_path.relative_to(ROOT)}"))
        pause(interactive)
        return proc.returncode or 1
    print(
        S.warn(f"앱을 시작했지만 포트 {port} 확인이 지연되고 있습니다. PID {proc.pid}")
    )
    pause(interactive)
    return 0

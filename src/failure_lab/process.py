from __future__ import annotations

import os
import signal
import time
from pathlib import Path

from .constant import APP


def read_cmdline(pid: int) -> str:
    try:
        data = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return data.replace(b"\0", b" ").decode(errors="replace").strip()


def listen_socket_inodes(port: int) -> set[str]:
    inodes: set[str] = set()
    port_hex = f"{port:04X}"
    for table in (Path("/proc/net/tcp"), Path("/proc/net/tcp6")):
        try:
            lines = table.read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            if len(fields) < 10:
                continue
            local_addr, state, inode = fields[1], fields[3], fields[9]
            if state == "0A" and local_addr.rsplit(":", 1)[-1].upper() == port_hex:
                inodes.add(inode)
    return inodes


def pids_for_socket_inodes(inodes: set[str]) -> set[int]:
    if not inodes:
        return set()
    pids: set[int] = set()
    for proc_dir in Path("/proc").glob("[0-9]*"):
        pid = int(proc_dir.name)
        fd_dir = proc_dir / "fd"
        try:
            fds = list(fd_dir.iterdir())
        except OSError:
            continue
        for fd in fds:
            try:
                target = os.readlink(fd)
            except OSError:
                continue
            if target.startswith("socket:[") and target[8:-1] in inodes:
                pids.add(pid)
                break
    return pids


def pids_listening_on_port(port: int) -> set[int]:
    return pids_for_socket_inodes(listen_socket_inodes(port))


def agent_process_pids() -> set[int]:
    pids: set[int] = set()
    app_path = str(APP.resolve())
    for proc_dir in Path("/proc").glob("[0-9]*"):
        pid = int(proc_dir.name)
        if pid == os.getpid():
            continue
        cmdline = read_cmdline(pid)
        if not cmdline:
            continue
        first = cmdline.split(" ", 1)[0]
        base = Path(first).name
        try:
            first_path = str(Path(first).resolve())
        except OSError:
            first_path = first
        if first_path == app_path or base.startswith("agent-app"):
            pids.add(pid)
    return pids


def child_pids(parent: int) -> set[int]:
    children: set[int] = set()
    for proc_dir in Path("/proc").glob("[0-9]*"):
        pid = int(proc_dir.name)
        try:
            status = (proc_dir / "status").read_text().splitlines()
        except OSError:
            continue
        for line in status:
            if line.startswith("PPid:") and line.split()[1] == str(parent):
                children.add(pid)
                break
    return children


def select_monitor_pid(port: int, launch_pid: int | None = None) -> int | None:
    """Select an agent TCP listener, preferring its worker over a launcher."""
    listeners = pids_listening_on_port(port)
    if launch_pid is None:
        candidates = listeners & agent_process_pids()
        return min(candidates) if candidates else None
    pending = [(launch_pid, 0)]
    seen: set[int] = set()
    candidates: list[tuple[int, int]] = []
    while pending:
        pid, depth = pending.pop()
        if pid in seen:
            continue
        seen.add(pid)
        if pid in listeners:
            candidates.append((depth, -pid))
        pending.extend((child, depth + 1) for child in child_pids(pid))
    return -max(candidates)[1] if candidates else None


def pid_tree(roots: set[int]) -> list[int]:
    seen: set[int] = set()

    def visit(pid: int) -> None:
        if pid in seen or pid == os.getpid():
            return
        seen.add(pid)
        for child in child_pids(pid):
            visit(child)

    for root in roots:
        visit(root)
    return sorted(seen, key=lambda pid: len(child_pids(pid)), reverse=True)


def terminate_pids(pids: set[int]) -> set[int]:
    targets = pid_tree(pids)
    if not targets:
        return set()
    for sig in (signal.SIGTERM, signal.SIGKILL):
        alive: list[int] = []
        for pid in targets:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                continue
            try:
                os.kill(pid, sig)
                alive.append(pid)
            except ProcessLookupError:
                continue
            except PermissionError:
                pass
        if sig == signal.SIGTERM:
            deadline = time.time() + 3
            while time.time() < deadline:
                if all(not Path(f"/proc/{pid}").exists() for pid in alive):
                    break
                time.sleep(0.1)
    return set(targets)

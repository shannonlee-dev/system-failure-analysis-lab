"""실제 서비스 없이 모니터 대상과 방화벽 상태를 검증한다."""

import subprocess
from pathlib import Path

import pytest

from failure_lab import process

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("state,healthy", [("active", True), ("inactive", False)])
def test_firewall_status_requires_exact_active(state, healthy):
    text = (ROOT / "scripts/monitor.sh").read_text()
    start = text.index("check_firewall() {")
    end = text.index("\n}", start) + 2
    command = (
        f"ufw() {{ printf 'Status: {state}\\n'; }}; "
        "warn() { printf 'WARNING:%s\\n' \"$*\"; }; "
        + text[start:end]
        + "; check_firewall"
    )
    output = subprocess.check_output(["bash", "-c", command], text=True)
    assert ("[OK] UFW active" in output) is healthy


def test_monitor_selects_listener_child_instead_of_launcher(monkeypatch):
    children = {100: {101}, 101: {102}, 102: set()}
    monkeypatch.setattr(process, "child_pids", lambda pid: children.get(pid, set()))
    monkeypatch.setattr(process, "pids_listening_on_port", lambda port: {102, 999})
    assert process.select_monitor_pid(15034, launch_pid=100) == 102


def test_monitor_rejects_unrelated_listener(monkeypatch):
    monkeypatch.setattr(process, "child_pids", lambda pid: set())
    monkeypatch.setattr(process, "pids_listening_on_port", lambda port: {999})
    assert process.select_monitor_pid(15034, launch_pid=100) is None


def test_monitor_without_launcher_requires_agent_listener(monkeypatch):
    monkeypatch.setattr(process, "pids_listening_on_port", lambda port: {20, 30})
    monkeypatch.setattr(process, "agent_process_pids", lambda: {30, 40})
    assert process.select_monitor_pid(15034) == 30

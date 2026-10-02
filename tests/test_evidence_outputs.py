"""가짜 앱·모니터만 실행해 수집 결과와 기존 증거 보호를 검증한다."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def isolated_repo(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ["collect_real_evidence.sh", "monitor_cpu_sampling.sh"]:
        shutil.copyfile(ROOT / "scripts" / name, scripts / name)
    app = tmp_path / "assets/agent-app-leak/agent-app-leak"
    app.parent.mkdir(parents=True)
    app.write_text('#!/bin/bash\nprintf launched > "$LAUNCH_MARKER"\nexit 9\n')
    app.chmod(0o750)
    monitor = scripts / "monitor.sh"
    monitor.write_text('#!/bin/bash\nprintf "sample\\n" >> "$MONITOR_LOG_FILE"\n')
    monitor.chmod(0o750)
    return tmp_path


def test_collection_rejects_existing_output_before_launch(isolated_repo):
    output = isolated_repo / "existing"
    output.mkdir()
    raw = output / "stdout.log"
    raw.write_text("original evidence")
    marker = isolated_repo / "launched"
    result = subprocess.run(
        [
            "bash",
            str(isolated_repo / "scripts/collect_real_evidence.sh"),
            "--output",
            str(output),
        ],
        env=dict(os.environ, LAUNCH_MARKER=str(marker)),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0
    assert raw.read_text() == "original evidence"
    assert not marker.exists()


def test_cpu_sampling_preserves_existing_raw_file(isolated_repo):
    output = isolated_repo / "evidence/cpu/spike/monitor_cpu.log"
    output.parent.mkdir(parents=True)
    output.write_text("original samples")
    result = subprocess.run(
        [
            "bash",
            str(isolated_repo / "scripts/monitor_cpu_sampling.sh"),
            "--output",
            str(output),
        ],
        env=dict(os.environ, DURATION="1", INTERVAL="0.5"),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0
    assert output.read_text() == "original samples"


def test_scenario_records_app_exit_and_monitor_failure(tmp_path):
    script = (ROOT / "scripts/collect_real_evidence.sh").read_text()
    begin = script.index("run_scenario() {")
    end = script.index("\n}\n", begin) + 2
    fake_app = tmp_path / "app"
    fake_app.write_text("#!/bin/bash\nexit 9\n")
    fake_app.chmod(0o750)
    command = (
        f"EVIDENCE_DIR={tmp_path}; RUN_ROOT={tmp_path}; APP={fake_app}; PORT=15034; MONITOR=/bin/false; "
        "wait_for_ready_or_exit() { return 0; }; kill() { return 0; }; kill_tree() { :; }; "
        + script[begin:end]
        + "; run_scenario demo demo 50 10 false 0 1 0"
    )
    result = subprocess.run(
        ["bash", "-c", command], capture_output=True, text=True, check=False
    )
    status = tmp_path / "demo/exit-status.txt"
    assert status.exists(), result.stdout + result.stderr
    fields = dict(line.split("=", 1) for line in status.read_text().splitlines())
    assert fields["app_exit_code"] == "9"
    assert fields["monitor_failures"] == "1"
    assert result.returncode != 0


def test_analysis_rejects_existing_output(tmp_path):
    output = tmp_path / "cpu.csv"
    output.write_text("saved result")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "failure_lab.cpu_spike",
            "--input",
            str(ROOT / "evidence/cpu/spike/monitor_cpu.log"),
            "--csv",
            str(output),
            "--report",
            str(tmp_path / "cpu.md"),
            "--plot",
            str(tmp_path / "cpu.png"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert output.read_text() == "saved result"


def test_process_capture_reports_tool_failure(tmp_path):
    text = (ROOT / "scripts/collect_real_evidence.sh").read_text()
    begin = text.index("write_ps_top_sample() {")
    end = text.index("\n}\n", begin) + 2
    output = tmp_path / "ps.log"
    command = (
        "ps() { return 6; }; pgrep() { return 1; }; top() { return 8; }; "
        + text[begin:end]
        + f"; write_ps_top_sample 123 {output}"
    )
    result = subprocess.run(["bash", "-c", command], check=False)
    assert result.returncode != 0
    assert "exit_code=6" in output.read_text()
    assert "exit_code=8" in output.read_text()


@pytest.mark.parametrize("command", ["collect", "sample-cpu"])
def test_cli_accepts_separate_output_path(command):
    from failure_lab.cli import build_parser

    args = build_parser().parse_args([command, "--output", "/tmp/new-output"])
    assert args.output == Path("/tmp/new-output")


def test_sampler_defaults_use_consistent_interval_and_new_run(isolated_repo):
    env = dict(os.environ)
    env.pop("DURATION", None)
    env.pop("INTERVAL", None)
    result = subprocess.run(
        ["bash", str(isolated_repo / "scripts/monitor_cpu_sampling.sh")],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    outputs = list(
        (isolated_repo / ".runtime/cpu-samples").glob("run-*/monitor_cpu.log")
    )
    assert len(outputs) == 1
    assert len(outputs[0].read_text().splitlines()) == 300
    assert not (isolated_repo / "evidence").exists()


def test_explicit_analysis_overwrite_preserves_input(tmp_path):
    output = tmp_path / "cpu.csv"
    output.write_text("old output")
    source = tmp_path / "source.log"
    source.write_text(
        "[2026-10-02 12:00:00] PID:1 CPU:0% MEM:1% DISK_USED:1%\n"
        "[2026-10-02 12:00:01] PID:1 CPU:10% MEM:1% DISK_USED:1%\n"
    )
    before = source.read_bytes()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "failure_lab.cpu_spike",
            "--input",
            str(source),
            "--csv",
            str(output),
            "--report",
            str(tmp_path / "cpu.md"),
            "--plot",
            str(tmp_path / "cpu.png"),
            "--overwrite",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert len(output.read_text().splitlines()) == 3
    assert source.read_bytes() == before

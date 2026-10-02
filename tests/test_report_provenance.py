"""보고서의 수치·인용·분석 원본을 현재 증거에 연결한다."""

import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_oom_report_quotes_the_current_logs_and_sample_counts():
    report = (ROOT / "reports/oom.md").read_text()
    for name in ["memory-50", "memory-128"]:
        directory = ROOT / "evidence/oom" / name
        log = (directory / "agent_app.log").read_text()
        pid = re.search(r"Self-terminating process (\d+)", log).group(1)
        assert f"Self-terminating process {pid}" in report
        timestamps = re.findall(r"^(\S+ \S+) \[INFO\] \[MemoryWorker\]", log, re.M)
        assert timestamps[0] in report
        assert timestamps[-1] in report
    assert "모니터 샘플 2개" in report
    assert "RSS 1.9MB" in report
    assert "워커의 RSS 증가를 입증하지 못한다" in report


def test_cpu_report_quotes_the_current_threshold():
    log = (ROOT / "evidence/cpu/cpu-max-100/agent_app.log").read_text()
    quoted = re.search(r"CPU Threshold Violated! \((.+?)%\)", log).group(1)
    report = (ROOT / "reports/cpu.md").read_text()
    assert f"CPU Threshold Violated! ({quoted}%)" in report
    assert "51.12%" in report
    assert "ps_top.log`는 비어" in report


def test_generated_report_records_input_digest_without_claiming_new_experiment(
    tmp_path,
):
    source = ROOT / "evidence/cpu/spike/monitor_cpu.log"
    report = tmp_path / "cpu.md"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "failure_lab.cpu_spike",
            "--input",
            str(source),
            "--csv",
            str(tmp_path / "cpu.csv"),
            "--report",
            str(report),
            "--plot",
            str(tmp_path / "cpu.png"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    text = report.read_text()
    assert hashlib.sha256(source.read_bytes()).hexdigest() in text
    assert str(source) in text
    assert "저장된 로그의 재분석" in text
    assert "분석 샘플 수: 600개" in text
    assert "탐지된 급상승 구간 수: 36개" in text

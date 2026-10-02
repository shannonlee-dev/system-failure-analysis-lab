"""대상 앱 실행 없이 저장된 CPU 로그와 분석 출력을 검증한다."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.smoke


def test_experiment_cli_syntax_check():
    result = subprocess.run(
        [sys.executable, "-m", "failure_lab", "check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cpu_analysis_outputs(tmp_path):
    csv, report, plot = tmp_path / "cpu.csv", tmp_path / "cpu.md", tmp_path / "cpu.png"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "failure_lab.cpu_spike",
            "--input",
            str(ROOT / "evidence/cpu/spike/monitor_cpu.log"),
            "--csv",
            str(csv),
            "--report",
            str(report),
            "--plot",
            str(plot),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(csv.read_text().splitlines()) > 2
    assert report.stat().st_size > 0
    if importlib.util.find_spec("matplotlib") is not None:
        assert plot.stat().st_size > 0

"""CPU 파싱·변화율·급상승 구간의 기존 분석 규칙을 검증한다."""

import datetime as dt

from failure_lab.cpu_spike.analysis import (
    compute_rates,
    find_spike_windows,
    parse_samples,
)
from failure_lab.cpu_spike.model import CpuSample


def test_noise_is_ignored_and_fractional_interval_detects_peak():
    samples = parse_samples(
        [
            "잘못된 로그",
            "[2024-01-01 00:00:00.000] PID:1 CPU:10% MEM:1% DISK_USED:2%",
            "[2024-01-01 00:00:00.500] PID:1 CPU:90% MEM:1% DISK_USED:2%",
            "[2024-01-01 00:00:01.000] PID:1 CPU:20% MEM:1% DISK_USED:2%",
        ]
    )
    rows = compute_rates(samples)
    assert len(rows) == 3 and rows[1].rate == 160.0
    windows = find_spike_windows(rows)
    assert len(windows) == 1 and windows[0].peak_cpu == 90.0
    assert windows[0].delta_t == 0.5


def test_duplicate_timestamps_do_not_divide_by_zero():
    timestamp = dt.datetime(2024, 1, 1)
    rows = compute_rates([CpuSample(timestamp, 0), CpuSample(timestamp, 100)])
    assert rows[1].delta_t == 0 and rows[1].rate == 0

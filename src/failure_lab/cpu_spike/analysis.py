from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterable

from .model import CpuSample, RateRow, SpikeWindow

LINE_RE = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)\]\s+"
    r"PID:(?P<pid>\d+)\s+"
    r"CPU:(?P<cpu>[0-9.]+)%\s+"
    r"MEM:(?P<mem>[0-9.]+)%\s+"
    r"DISK_USED:(?P<disk>[0-9.]+)%$"
)


def parse_line(line: str) -> CpuSample:
    match = LINE_RE.search(line)
    if not match:
        raise ValueError("monitor.log 형식이 아닙니다.")

    ts_text = match.group("ts")
    ts_format = "%Y-%m-%d %H:%M:%S.%f" if "." in ts_text else "%Y-%m-%d %H:%M:%S"
    return CpuSample(
        timestamp=dt.datetime.strptime(ts_text, ts_format),
        cpu=float(match.group("cpu")),
    )


def parse_samples(lines: Iterable[str]) -> list[CpuSample]:
    samples = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            samples.append(parse_line(line))
        except ValueError:
            continue
    return samples


def compute_rates(samples: list[CpuSample]) -> list[RateRow]:
    rows: list[RateRow] = []
    prev_sample: CpuSample | None = None
    for sample in samples:
        if prev_sample is None:
            rows.append(RateRow(sample.timestamp, sample.cpu, 0.0, 0.0, 0.0))
        else:
            delta_t = max(
                0.0, (sample.timestamp - prev_sample.timestamp).total_seconds()
            )
            delta_cpu = sample.cpu - prev_sample.cpu
            rate = 0.0 if delta_t == 0 else delta_cpu / delta_t
            rows.append(RateRow(sample.timestamp, sample.cpu, delta_cpu, delta_t, rate))
        prev_sample = sample

    marked = list(rows)
    for index in range(1, len(marked) - 1):
        prev_cpu = marked[index - 1].cpu
        cpu = marked[index].cpu
        next_cpu = marked[index + 1].cpu
        if cpu > prev_cpu and cpu >= next_cpu:
            row = marked[index]
            marked[index] = RateRow(
                row.timestamp,
                row.cpu,
                row.delta_cpu,
                row.delta_t,
                row.rate,
                is_local_max=True,
                is_spike=True,
            )
    return marked


def find_spike_windows(rows: list[RateRow]) -> list[SpikeWindow]:
    windows = []
    for index, row in enumerate(rows):
        if not row.is_spike or index == 0:
            continue
        windows.append(
            SpikeWindow(
                start=rows[index - 1].timestamp,
                end=row.timestamp,
                peak_ts=row.timestamp,
                peak_cpu=row.cpu,
                delta_cpu=row.delta_cpu,
                delta_t=row.delta_t,
                rate=row.rate,
            )
        )
    return windows

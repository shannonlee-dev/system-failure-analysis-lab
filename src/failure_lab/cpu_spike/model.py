from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class CpuSample:
    timestamp: dt.datetime
    cpu: float


@dataclass(frozen=True)
class RateRow:
    timestamp: dt.datetime
    cpu: float
    delta_cpu: float
    delta_t: float
    rate: float
    is_local_max: bool = False
    is_spike: bool = False


@dataclass(frozen=True)
class SpikeWindow:
    start: dt.datetime
    end: dt.datetime
    peak_ts: dt.datetime
    peak_cpu: float
    delta_cpu: float
    delta_t: float
    rate: float

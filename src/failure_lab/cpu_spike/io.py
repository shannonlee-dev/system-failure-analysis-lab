from __future__ import annotations

import csv
from pathlib import Path

from .analysis import parse_samples
from .model import CpuSample, RateRow


def read_samples(path: Path) -> list[CpuSample]:
    with path.open("r", encoding="utf-8") as file:
        return parse_samples(file)


def write_csv(rows: list[RateRow], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "timestamp",
                "cpu",
                "delta_cpu",
                "delta_t",
                "rate",
                "is_local_max",
                "is_spike",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.timestamp.isoformat(),
                    f"{row.cpu:.2f}",
                    f"{row.delta_cpu:.2f}",
                    f"{row.delta_t:.2f}",
                    f"{row.rate:.2f}",
                    "1" if row.is_local_max else "0",
                    "1" if row.is_spike else "0",
                ]
            )

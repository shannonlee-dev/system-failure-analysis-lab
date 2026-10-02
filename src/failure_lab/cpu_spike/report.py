from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

from .model import RateRow, SpikeWindow


def fmt_ts(ts) -> str:
    return ts.isoformat(sep=" ", timespec="milliseconds")


def write_report(
    out_path: Path,
    rows: list[RateRow],
    windows: list[SpikeWindow],
    plot_path: Path | None,
    csv_path: Path,
    input_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    total = len(rows)
    spike_count = len(windows)
    start_ts = rows[0].timestamp
    end_ts = rows[-1].timestamp
    duration_sec = (end_ts - start_ts).total_seconds()
    cpu_vals = [row.cpu for row in rows]

    avg_cpu = sum(cpu_vals) / len(cpu_vals)
    max_cpu = max(cpu_vals)
    min_cpu = min(cpu_vals)

    max_cpu_row = max(rows, key=lambda row: row.cpu)
    min_cpu_row = min(rows, key=lambda row: row.cpu)
    max_rate_row = max(rows, key=lambda row: row.rate)
    min_rate_row = min(rows, key=lambda row: row.rate)

    with out_path.open("w", encoding="utf-8") as file:
        file.write("# CPU 사용률 및 극대값 기반 급상승 구간 분석 리포트\n\n")
        file.write("## 1. 분석 개요\n\n")
        file.write(
            "이 결과는 저장된 로그의 재분석이며 새 장애 실험의 관측 결과가 아니다.\n\n"
        )
        file.write(f"- 입력 로그: `{input_path}`\n")
        file.write(
            f"- 입력 SHA-256: `{hashlib.sha256(input_path.read_bytes()).hexdigest()}`\n"
        )
        file.write(f"- 재분석 시각: {dt.datetime.now().astimezone().isoformat()}\n\n")
        file.write(
            "본 리포트는 `monitor.sh`로 수집한 CPU 사용률 로그를 기반으로, "
            "프로세스의 CPU 사용률 변화와 순간적인 증가 구간을 분석한 결과이다.\n\n"
        )
        file.write(
            "CPU 사용률 자체뿐 아니라, 연속된 두 샘플 사이의 CPU 변화량을 시간 차이로 나눈 "
            "`Delta CPU / Delta t` 값을 계산하였다. 이후 어떤 샘플이 직전 샘플보다 크고 "
            "다음 샘플보다 크거나 같은 극대값으로 확인되면, 그 샘플 직전 구간을 급상승 구간으로 판단하였다.\n\n"
        )

        file.write("## 2. 분석 방법\n\n")
        file.write("- 입력 로그에서 timestamp와 CPU 사용률 값을 추출하였다.\n")
        file.write("- 각 샘플 사이의 CPU 변화량을 계산하였다.\n")
        file.write(
            "- 변화량을 시간 간격으로 나누어 `Delta CPU / Delta t (%/s)`를 계산하였다.\n"
        )
        file.write(
            "- `CPU[i] > CPU[i-1]` 이고 `CPU[i] >= CPU[i+1]`이면 `CPU[i]`를 극대값으로 판단하였다.\n"
        )
        file.write(
            "- 극대값이 확인되면 `CPU[i-1] -> CPU[i]` 구간을 급상승 구간으로 표시하였다.\n\n"
        )

        file.write("## 3. 요약 결과\n\n")
        file.write(f"- 분석 샘플 수: {total}개\n")
        file.write(f"- 분석 시작 시각: {fmt_ts(start_ts)}\n")
        file.write(f"- 분석 종료 시각: {fmt_ts(end_ts)}\n")
        file.write(f"- 분석 구간 길이: {duration_sec:.2f}초\n")
        file.write(f"- 평균 CPU 사용률: {avg_cpu:.2f}%\n")
        file.write(
            f"- 최대 CPU 사용률: {max_cpu:.2f}% at {fmt_ts(max_cpu_row.timestamp)}\n"
        )
        file.write(
            f"- 최소 CPU 사용률: {min_cpu:.2f}% at {fmt_ts(min_cpu_row.timestamp)}\n"
        )
        file.write(
            f"- 최대 CPU 증가율: {max_rate_row.rate:.2f}%/s at {fmt_ts(max_rate_row.timestamp)}\n"
        )
        file.write(
            f"- 최대 CPU 감소율: {min_rate_row.rate:.2f}%/s at {fmt_ts(min_rate_row.timestamp)}\n"
        )
        file.write(f"- 탐지된 급상승 구간 수: {spike_count}개\n\n")

        file.write("## 4. 산출 파일\n\n")
        file.write(f"- CSV 분석 결과: `{csv_path}`\n")
        if plot_path:
            file.write(f"- CPU 그래프: `{plot_path}`\n")
        file.write("\n")

        file.write("## 5. CPU 급상승 구간 분석\n\n")
        if not windows:
            file.write(
                "극대값으로 확인된 샘플이 없어 급상승 구간은 확인되지 않았다.\n\n"
            )
        else:
            file.write(
                "다음 구간에서 극대값이 생성되어 직전 구간을 급상승 구간으로 표시하였다.\n\n"
            )
            for index, window in enumerate(windows, 1):
                file.write(
                    f"- 구간 {index}: {fmt_ts(window.start)} -> {fmt_ts(window.end)}, "
                    f"극대값 시각={fmt_ts(window.peak_ts)}, "
                    f"극대 CPU={window.peak_cpu:.2f}%, "
                    f"변화율={window.rate:.2f}%/s\n"
                )
            file.write("\n")

        file.write("## 6. 해석 및 결론\n\n")
        if max_cpu < 5:
            file.write(
                f"분석 구간에서 CPU 사용률의 최대값은 {max_cpu:.2f}%로, "
                "CPU 과점유를 입증하는 자료라기보다는 낮은 CPU 사용률 유지의 보조 증거로 보는 것이 적절하다.\n\n"
            )
        elif max_cpu < 50:
            file.write(
                f"분석 구간에서 CPU 사용률의 최대값은 {max_cpu:.2f}%로, "
                "일부 상승은 있었지만 CPU 과점유 상태라고 보기는 어렵다.\n\n"
            )
        else:
            file.write(
                f"분석 구간에서 CPU 사용률이 최대 {max_cpu:.2f}%까지 상승하였다. "
                "이는 CPU 사용률 급등 구간으로 볼 수 있다.\n\n"
            )

        file.write(
            "최종 판단은 본 그래프만으로 단정하지 않고 `agent_app.log`, `top/ps` 출력, "
            "프로세스 종료 코드, `CpuWorker` 관련 로그를 함께 근거로 삼는 것이 적절하다.\n"
        )

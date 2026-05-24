#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import math
import os
import re
from typing import List, Tuple

LINE_RE = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+"
    r"PID:(?P<pid>\d+)\s+"
    r"CPU:(?P<cpu>[0-9.]+)%\s+"
    r"MEM:(?P<mem>[0-9.]+)%\s+"
    r"RSS_MB:(?P<rss>[0-9.]+)\s+"
    r"DISK_USED:(?P<disk>[0-9.]+)%$"
)


def parse_line(line: str) -> Tuple[dt.datetime, float]:
    match = LINE_RE.search(line)
    if not match:
        raise ValueError("unrecognized mission monitor.log format")

    ts = dt.datetime.strptime(match.group("ts"), "%Y-%m-%d %H:%M:%S")
    cpu = float(match.group("cpu"))
    return ts, cpu


def compute_rates(samples: List[Tuple[dt.datetime, float]]):
    rows = []
    prev_ts = None
    prev_cpu = None
    for ts, cpu in samples:
        if prev_ts is None:
            rows.append((ts, cpu, 0.0, 0.0, 0.0))
        else:
            delta_t = (ts - prev_ts).total_seconds()
            if delta_t <= 0:
                delta_t = 0.0
            delta_cpu = cpu - prev_cpu
            rate = 0.0 if delta_t == 0 else delta_cpu / delta_t
            rows.append((ts, cpu, delta_cpu, delta_t, rate))
        prev_ts = ts
        prev_cpu = cpu
    return rows


def find_spike_windows(rows, threshold: float):
    windows = []
    current = None
    for ts, cpu, delta_cpu, delta_t, rate in rows:
        if rate >= threshold:
            if current is None:
                current = {
                    "start": ts,
                    "end": ts,
                    "max_rate": rate,
                    "max_cpu": cpu,
                }
            else:
                current["end"] = ts
                current["max_rate"] = max(current["max_rate"], rate)
                current["max_cpu"] = max(current["max_cpu"], cpu)
        else:
            if current is not None:
                windows.append(current)
                current = None
    if current is not None:
        windows.append(current)
    return windows


def write_csv(rows, out_path: str, threshold: float):
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "cpu", "delta_cpu", "delta_t", "rate", "is_spike"])
        for ts, cpu, delta_cpu, delta_t, rate in rows:
            writer.writerow(
                [
                    ts.isoformat(),
                    f"{cpu:.2f}",
                    f"{delta_cpu:.2f}",
                    f"{delta_t:.2f}",
                    f"{rate:.2f}",
                    "1" if rate >= threshold else "0",
                ]
            )

def write_report(out_path: str, rows, windows, threshold: float, plot_path: str, csv_path: str):
    def fmt_ts(ts):
        return ts.strftime("%Y-%m-%d %H:%M:%S")

    total = len(rows)
    spike_count = len(windows)

    start_ts = rows[0][0]
    end_ts = rows[-1][0]
    duration_sec = (end_ts - start_ts).total_seconds()

    cpu_vals = [r[1] for r in rows]
    rate_vals = [r[4] for r in rows]

    avg_cpu = sum(cpu_vals) / len(cpu_vals)
    max_cpu = max(cpu_vals)
    min_cpu = min(cpu_vals)

    max_cpu_row = max(rows, key=lambda r: r[1])
    min_cpu_row = min(rows, key=lambda r: r[1])
    max_rate_row = max(rows, key=lambda r: r[4])
    min_rate_row = min(rows, key=lambda r: r[4])

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# CPU 사용률 및 변화율 분석 리포트\n\n")

        f.write("## 1. 분석 개요\n\n")
        f.write(
            "본 리포트는 `monitor.sh`로 수집한 CPU 사용률 로그를 기반으로, "
            "프로세스의 CPU 사용률 변화와 순간적인 증가 구간을 분석한 결과이다.\n\n"
        )
        f.write(
            "CPU 사용률 자체뿐 아니라, 연속된 두 샘플 사이의 CPU 변화량을 시간 차이로 나눈 "
            "`ΔCPU/Δt` 값을 계산하여 CPU 사용률이 얼마나 빠르게 변했는지도 함께 확인하였다.\n\n"
        )

        f.write("## 2. 분석 방법\n\n")
        f.write("- 입력 로그에서 timestamp와 CPU 사용률 값을 추출하였다.\n")
        f.write("- 각 샘플 사이의 CPU 변화량을 계산하였다.\n")
        f.write("- 변화량을 시간 간격으로 나누어 `ΔCPU/Δt (%/s)`를 계산하였다.\n")
        f.write(f"- `ΔCPU/Δt >= {threshold:.2f} %/s`인 구간을 CPU 급상승 후보 구간으로 판단하였다.\n\n")
        f.write(
            "> 참고: 본 분석의 `ΔCPU/Δt`는 연속 함수의 미분값이 아니라, "
            "로그 샘플 간 차이를 이용한 이산적인 변화율이다.\n\n"
        )

        f.write("## 3. 요약 결과\n\n")
        f.write(f"- 분석 샘플 수: {total}개\n")
        f.write(f"- 분석 시작 시각: {fmt_ts(start_ts)}\n")
        f.write(f"- 분석 종료 시각: {fmt_ts(end_ts)}\n")
        f.write(f"- 분석 구간 길이: {duration_sec:.2f}초\n")
        f.write(f"- 평균 CPU 사용률: {avg_cpu:.2f}%\n")
        f.write(f"- 최대 CPU 사용률: {max_cpu:.2f}% at {fmt_ts(max_cpu_row[0])}\n")
        f.write(f"- 최소 CPU 사용률: {min_cpu:.2f}% at {fmt_ts(min_cpu_row[0])}\n")
        f.write(f"- 최대 CPU 증가율: {max_rate_row[4]:.2f}%/s at {fmt_ts(max_rate_row[0])}\n")
        f.write(f"- 최대 CPU 감소율: {min_rate_row[4]:.2f}%/s at {fmt_ts(min_rate_row[0])}\n")
        f.write(f"- 탐지된 급상승 구간 수: {spike_count}개\n\n")

        f.write("## 4. 산출 파일\n\n")
        f.write(f"- CSV 분석 결과: `{csv_path}`\n")
        if plot_path:
            f.write(f"- CPU 그래프: `{plot_path}`\n")
        f.write("\n")

        f.write("## 5. CPU 급상승 구간 분석\n\n")
        if not windows:
            f.write(
                f"`ΔCPU/Δt >= {threshold:.2f} %/s` 기준을 초과한 구간은 확인되지 않았다.\n\n"
            )
            f.write(
                "따라서 이 로그 구간에서는 CPU 사용률이 순간적으로 크게 폭증했다고 보기 어렵다. "
                "CPU 사용률은 일부 진동은 있었지만, 전체적으로 낮은 범위에서 움직인 것으로 해석된다.\n\n"
            )
        else:
            f.write(
                f"다음 구간에서 `ΔCPU/Δt >= {threshold:.2f} %/s` 조건을 만족하는 CPU 급상승 후보가 확인되었다.\n\n"
            )
            for idx, window in enumerate(windows, 1):
                start = fmt_ts(window["start"])
                end = fmt_ts(window["end"])
                f.write(
                    f"- 구간 {idx}: {start} → {end}, "
                    f"최대 변화율={window['max_rate']:.2f}%/s, "
                    f"구간 내 최대 CPU={window['max_cpu']:.2f}%\n"
                )
            f.write("\n")

        f.write("## 6. 해석 및 결론\n\n")
        if max_cpu < 5:
            f.write(
                f"분석 구간에서 CPU 사용률의 최대값은 {max_cpu:.2f}%로, "
                "절대적인 CPU 점유율은 매우 낮은 수준이었다. "
                "따라서 이 그래프는 CPU 과점유를 입증하는 자료라기보다는, "
                "프로세스가 높은 연산 부하 없이 낮은 CPU 사용률을 유지했다는 보조 증거로 보는 것이 적절하다.\n\n"
            )
        elif max_cpu < 50:
            f.write(
                f"분석 구간에서 CPU 사용률의 최대값은 {max_cpu:.2f}%로, "
                "일부 상승은 있었지만 CPU 과점유 상태라고 보기는 어렵다. "
                "추가적으로 애플리케이션 로그의 `[CpuWorker]` 또는 `[CRITICAL]` 메시지와 함께 해석해야 한다.\n\n"
            )
        else:
            f.write(
                f"분석 구간에서 CPU 사용률이 최대 {max_cpu:.2f}%까지 상승하였다. "
                "이는 CPU 사용률 급등 구간으로 볼 수 있으며, "
                "애플리케이션 로그의 CPU 보호 로직 동작 여부와 함께 원인을 분석할 필요가 있다.\n\n"
            )

        f.write(
            "최종적으로, CPU 장애 여부는 본 그래프만으로 단정하지 않고 "
            "`agent_app.log`, `top/ps` 출력, 프로세스 종료 코드, "
            "그리고 `CpuWorker` 관련 로그를 함께 근거로 판단하는 것이 적절하다.\n"
        )

def try_plot(rows, out_path: str, threshold: float):
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return False

    timestamps = [r[0] for r in rows]
    cpu_vals = [r[1] for r in rows]
    rate_vals = [r[4] for r in rows]

    fig, ax1 = plt.subplots(figsize=(14, 6))
    ax1.plot(timestamps, cpu_vals, color="#1f77b4", label="CPU (%)", linewidth=1.5)
    ax1.set_ylabel("CPU (%)")
    ax1.set_xlabel("Time")
    ax1.set_ylim(0, 5)

    ax2 = ax1.twinx()
    ax2.plot(timestamps, rate_vals, color="#d62728", label="ΔCPU/Δt (%/s)", linewidth=1.0, alpha=0.7)
    ax2.set_ylabel("ΔCPU/Δt (%/s)")

    # identify contiguous windows where rate >= threshold
    above = [1 if r >= threshold else 0 for r in rate_vals]
    windows = []
    start_idx = None
    for i, val in enumerate(above):
        if val == 1 and start_idx is None:
            start_idx = i
        if val == 0 and start_idx is not None:
            windows.append((start_idx, i - 1))
            start_idx = None
    if start_idx is not None:
        windows.append((start_idx, len(above) - 1))

    for (i_start, i_end) in windows:
        ts_start = timestamps[i_start]
        ts_end = timestamps[i_end]
        ax1.axvspan(ts_start, ts_end, color="#ffcccc", alpha=0.25)

    # argmax on rate
    if len(rate_vals) > 0:
        max_rate = max(rate_vals)
        argmax_idx = rate_vals.index(max_rate)
        arg_ts = timestamps[argmax_idx]
        arg_rate = rate_vals[argmax_idx]
        arg_cpu = cpu_vals[argmax_idx]

        # mark on rate axis
        ax2.scatter([arg_ts], [arg_rate], color="#8b0000", s=60, zorder=5)
        ax2.annotate(f"max ΔCPU/Δt={arg_rate:.2f}%/s", xy=(arg_ts, arg_rate), xytext=(10, 10), textcoords="offset points", color="#8b0000")

        # mark corresponding CPU peak on CPU axis
        ax1.scatter([arg_ts], [arg_cpu], color="#000000", s=40, marker='o', zorder=6)
        ax1.annotate(f"CPU={arg_cpu:.2f}%", xy=(arg_ts, arg_cpu), xytext=(10, -15), textcoords="offset points", color="#000000")

        # draw horizontal dashed line at max rate on the rate axis (user-requested)
        ax2.axhline(arg_rate, color="#8b0000", linestyle="--", linewidth=1.2, alpha=0.8)

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    # place legend above plot to avoid overlap
    ax1.legend(lines + lines2, labels + labels2, loc='upper center', bbox_to_anchor=(0.5, 1.12), ncol=2)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches='tight', dpi=150)
    plt.close(fig)
    return True


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    submission_dir = os.path.abspath(os.path.join(script_dir, ".."))
    default_input = os.path.join(submission_dir, "evidence", "cpu", "spike", "monitor_cpu.log")
    default_csv = os.path.join(submission_dir, "evidence", "cpu", "spike", "cpu_spike.csv")
    default_plot = os.path.join(submission_dir, "evidence", "cpu", "spike", "cpu_spike.png")
    default_report = os.path.join(submission_dir, "evidence", "cpu", "spike", "cpu_spike.md")

    parser = argparse.ArgumentParser(description="Analyze CPU spike windows from monitor.sh logs.")
    parser.add_argument("--input", default=default_input, help="Input monitor_cpu.log")
    parser.add_argument("--csv", default=default_csv, help="Output CSV path")
    parser.add_argument("--report", default=default_report, help="Output Markdown report path")
    parser.add_argument("--plot", default=default_plot, help="Output PNG path")
    parser.add_argument("--threshold", type=float, default=0.5, help="Spike threshold in %/s")

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        raise SystemExit(f"Input not found: {args.input}")

    samples = []
    with open(args.input, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                samples.append(parse_line(line))
            except ValueError:
                continue

    if len(samples) < 2:
        raise SystemExit("Not enough samples to analyze.")

    rows = compute_rates(samples)
    windows = find_spike_windows(rows, args.threshold)

    os.makedirs(os.path.dirname(args.csv), exist_ok=True)
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    os.makedirs(os.path.dirname(args.plot), exist_ok=True)

    write_csv(rows, args.csv, args.threshold)
    plot_ok = try_plot(rows, args.plot, args.threshold)
    write_report(args.report, rows, windows, args.threshold, args.plot if plot_ok else "", args.csv)

    print(f"[OK] CSV: {args.csv}")
    if plot_ok:
        print(f"[OK] Plot: {args.plot}")
    else:
        print("[WARN] Plot skipped (matplotlib not available)")
    print(f"[OK] Report: {args.report}")


if __name__ == "__main__":
    main()

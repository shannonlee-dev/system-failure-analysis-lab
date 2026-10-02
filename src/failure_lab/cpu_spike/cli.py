from __future__ import annotations

import argparse
from pathlib import Path

from .analysis import compute_rates, find_spike_windows
from .io import read_samples, write_csv
from .plot import try_plot
from .report import write_report

_CHECKOUT_DIR = Path(__file__).resolve().parents[3]
PROJECT_DIR = (
    _CHECKOUT_DIR if (_CHECKOUT_DIR / "pyproject.toml").is_file() else Path.cwd()
)
DEFAULT_SPIKE_DIR = PROJECT_DIR / "evidence" / "cpu" / "spike"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / ".runtime" / "cpu-analysis"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="monitor.sh 로그에서 CPU 급상승 구간을 분석합니다."
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_SPIKE_DIR / "monitor_cpu.log",
        type=Path,
        help="입력 로그 경로",
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_OUTPUT_DIR / "cpu_spike.csv",
        type=Path,
        help="CSV 출력 경로",
    )
    parser.add_argument(
        "--report",
        default=DEFAULT_OUTPUT_DIR / "cpu_spike.md",
        type=Path,
        help="Markdown 리포트 경로",
    )
    parser.add_argument(
        "--plot",
        default=DEFAULT_OUTPUT_DIR / "cpu_spike.png",
        type=Path,
        help="PNG 그래프 경로",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="기존 분석 출력 교체 허용"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.input.is_file():
        raise SystemExit(f"입력 파일을 찾을 수 없습니다: {args.input}")
    outputs = [path.resolve() for path in (args.csv, args.report, args.plot)]
    if args.input.resolve() in outputs or len(set(outputs)) != len(outputs):
        raise SystemExit("입력과 출력, 각 출력 경로는 서로 달라야 합니다.")
    if not args.overwrite and any(path.exists() for path in outputs):
        raise SystemExit("기존 출력이 있습니다. 새 경로나 --overwrite를 지정하세요.")

    samples = read_samples(args.input)
    if len(samples) < 2:
        raise SystemExit("분석할 샘플이 부족합니다.")

    rows = compute_rates(samples)
    windows = find_spike_windows(rows)

    write_csv(rows, args.csv)
    plot_ok = try_plot(rows, windows, args.plot)
    write_report(args.report, rows, windows, args.plot if plot_ok else None, args.csv)

    print(f"[OK] CSV: {args.csv}")
    if plot_ok:
        print(f"[OK] 그래프: {args.plot}")
    else:
        print("[WARN] matplotlib을 사용할 수 없어 그래프 생성을 건너뛰었습니다.")
    print(f"[OK] 리포트: {args.report}")
    return 0

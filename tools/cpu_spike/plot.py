from __future__ import annotations

import os
from pathlib import Path

from .model import RateRow, SpikeWindow


def try_plot(rows: list[RateRow], windows: list[SpikeWindow], out_path: Path) -> bool:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    try:
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except Exception:
        return False

    out_path.parent.mkdir(parents=True, exist_ok=True)
    timestamps = [row.timestamp for row in rows]
    cpu_vals = [row.cpu for row in rows]
    rate_vals = [row.rate for row in rows]
    peak_rows = [row for row in rows if row.is_local_max]

    top_windows = sorted(windows, key=lambda window: (window.peak_cpu, window.rate), reverse=True)[:8]
    top_peak_times = {window.peak_ts for window in top_windows}
    top_peak_rows = [row for row in peak_rows if row.timestamp in top_peak_times]

    fig, (ax_cpu, ax_rate) = plt.subplots(
        2,
        1,
        figsize=(14, 7),
        sharex=True,
        gridspec_kw={"height_ratios": [2.3, 1], "hspace": 0.08},
        constrained_layout=True,
    )
    fig.patch.set_facecolor("white")

    for ax in (ax_cpu, ax_rate):
        ax.grid(True, axis="y", color="#e5e7eb", linewidth=0.8)
        ax.grid(True, axis="x", color="#f3f4f6", linewidth=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    for window in top_windows:
        for ax in (ax_cpu, ax_rate):
            ax.axvspan(window.start, window.end, color="#f97316", alpha=0.10, linewidth=0)

    ax_cpu.step(timestamps, cpu_vals, where="post", color="#2563eb", linewidth=1.5, label="CPU (%)")
    ax_cpu.fill_between(timestamps, cpu_vals, step="post", color="#93c5fd", alpha=0.20)
    ax_cpu.set_ylabel("CPU (%)")
    ax_cpu.set_ylim(0, max(10, max(cpu_vals) * 1.18))
    ax_cpu.set_title("CPU Spike Analysis", loc="left", fontsize=14, fontweight="bold", pad=10)

    if peak_rows:
        ax_cpu.scatter(
            [row.timestamp for row in peak_rows],
            [row.cpu for row in peak_rows],
            color="#111827",
            s=14,
            alpha=0.45,
            label="local max",
            zorder=5,
        )

    if top_peak_rows:
        ax_cpu.scatter(
            [row.timestamp for row in top_peak_rows],
            [row.cpu for row in top_peak_rows],
            color="#f97316",
            edgecolor="#111827",
            linewidth=0.6,
            s=42,
            label="top peaks",
            zorder=6,
        )
        annotated_times = []
        annotation_offsets = [(0, 9), (0, 18), (0, 27), (0, 36), (0, 45)]
        for row in sorted(top_peak_rows, key=lambda item: item.cpu, reverse=True):
            if len(annotated_times) >= 5:
                break
            if any(abs((row.timestamp - ts).total_seconds()) < 3 for ts in annotated_times):
                continue
            offset = annotation_offsets[len(annotated_times)]
            ax_cpu.annotate(
                f"{row.cpu:.1f}%",
                xy=(row.timestamp, row.cpu),
                xytext=offset,
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color="#111827",
            )
            annotated_times.append(row.timestamp)

    ax_rate.plot(timestamps, rate_vals, color="#ef4444", linewidth=0.9, alpha=0.75, label="Delta CPU / sec")
    ax_rate.axhline(0, color="#6b7280", linewidth=0.8)
    ax_rate.set_ylabel("Delta (%/s)")
    ax_rate.set_xlabel("Time")
    if rate_vals:
        max_abs_rate = max(abs(value) for value in rate_vals)
        ax_rate.set_ylim(-max(20, max_abs_rate * 1.12), max(20, max_abs_rate * 1.12))

    locator = mdates.AutoDateLocator(minticks=5, maxticks=7)
    formatter = mdates.DateFormatter("%H:%M:%S")
    ax_rate.xaxis.set_major_locator(locator)
    ax_rate.xaxis.set_major_formatter(formatter)
    ax_rate.xaxis.get_offset_text().set_visible(False)

    handles, labels = [], []
    for ax in (ax_cpu, ax_rate):
        ax_handles, ax_labels = ax.get_legend_handles_labels()
        handles.extend(ax_handles)
        labels.extend(ax_labels)
    ax_cpu.legend(handles, labels, loc="upper right", frameon=False, ncol=3)

    fig.savefig(out_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return True

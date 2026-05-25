import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RESULTS = Path(__file__).parent / "results"

MODE_LABELS = {
    "rusttorust":   "Rust → Rust",
    "rusttocsharp": "Rust → C#",
    "csharptorust": "C# → Rust",
    "csharptocsharp": "C# → C#",
}

COLORS = {
    "rusttorust":   "#4c78a8",
    "rusttocsharp": "#f58518",
    "csharptorust": "#54a24b",
    "csharptocsharp": "#e45756",
}


def discover_intervals(mode_dir):
    intervals = set()
    for p in sorted(mode_dir.glob("latencies_*.csv")):
        m = re.search(r"latencies_(\d+)ms\.csv", p.name)
        if m:
            intervals.add(int(m.group(1)))
    return sorted(intervals)


def plot_latency(mode_dir, interval, mode_name):
    csv_path = mode_dir / f"latencies_{interval}ms.csv"
    if not csv_path.exists():
        return
    df = pd.read_csv(csv_path)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(df["seq"], df["latency_ms"], s=4, alpha=0.5, color=COLORS.get(mode_name, "#4c78a8"))
    if len(df) > 10:
        rolling = df["latency_ms"].rolling(20, min_periods=1).mean()
        ax.plot(df["seq"], rolling, color="black", linewidth=1.5, label="20-pt rolling avg")

    ax.set_xlabel("Request #")
    ax.set_ylabel("Latency (ms)")
    ax.set_title(f"{MODE_LABELS.get(mode_name, mode_name)} — Latency @ {interval}ms interval")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)

    lats = df["latency_ms"]
    stats = (
        f"min: {lats.min():.4f} ms\n"
        f"avg: {lats.mean():.4f} ms\n"
        f"p50: {lats.median():.4f} ms\n"
        f"p99: {lats.quantile(0.99):.4f} ms\n"
        f"max: {lats.max():.4f} ms"
    )
    ax.text(0.02, 0.97, stats, transform=ax.transAxes, fontsize=8,
            verticalalignment="top", bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.7))

    fig.tight_layout()
    fig.savefig(mode_dir / f"latency_{interval}ms.png", dpi=150)
    plt.close(fig)


def plot_cpu(mode_dir, interval, mode_name):
    csv_path = mode_dir / f"resources_{interval}ms.csv"
    if not csv_path.exists():
        return
    df = pd.read_csv(csv_path)
    if df.empty:
        return

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df["elapsed_s"], df["cpu_percent"], color=COLORS.get(mode_name, "#4c78a8"),
            linewidth=1.2)
    ax.set_xlabel("Elapsed Time (s)")
    ax.set_ylabel("CPU %")
    ax.set_title(f"{MODE_LABELS.get(mode_name, mode_name)} — CPU @ {interval}ms interval")
    ax.grid(True, alpha=0.3)

    peak = df["cpu_percent"].max()
    avg = df["cpu_percent"].mean()
    stats = f"peak: {peak:.1f}%\navg: {avg:.1f}%"
    ax.text(0.02, 0.97, stats, transform=ax.transAxes, fontsize=9,
            verticalalignment="top", bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.7))

    fig.tight_layout()
    fig.savefig(mode_dir / f"cpu_{interval}ms.png", dpi=150)
    plt.close(fig)


def plot_ram(mode_dir, interval, mode_name):
    csv_path = mode_dir / f"resources_{interval}ms.csv"
    if not csv_path.exists():
        return
    df = pd.read_csv(csv_path)
    if df.empty:
        return

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df["elapsed_s"], df["memory_mb"], color="#e45756", linewidth=1.2)
    ax.set_xlabel("Elapsed Time (s)")
    ax.set_ylabel("Memory (MB)")
    ax.set_title(f"{MODE_LABELS.get(mode_name, mode_name)} — RAM @ {interval}ms interval")
    ax.grid(True, alpha=0.3)

    peak = df["memory_mb"].max()
    avg = df["memory_mb"].mean()
    stats = f"peak: {peak:.2f} MB\navg: {avg:.2f} MB"
    ax.text(0.02, 0.97, stats, transform=ax.transAxes, fontsize=9,
            verticalalignment="top", bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.7))

    fig.tight_layout()
    fig.savefig(mode_dir / f"ram_{interval}ms.png", dpi=150)
    plt.close(fig)


def main():
    results_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS
    mode_dirs = sorted(d for d in results_dir.iterdir() if d.is_dir())

    if not mode_dirs:
        print(f"No mode directories found under {results_dir}")
        sys.exit(1)

    for mode_dir in mode_dirs:
        mode_name = mode_dir.name
        intervals = discover_intervals(mode_dir)
        if not intervals:
            continue
        print(f"  {mode_name}: {intervals}")
        for interval in intervals:
            plot_latency(mode_dir, interval, mode_name)
            plot_cpu(mode_dir, interval, mode_name)
            plot_ram(mode_dir, interval, mode_name)

    print("  Done")


if __name__ == "__main__":
    main()

"""
Chunk Analysis & Comparison Script
====================================
Reads all strategy JSONL outputs and produces:
  - Per-strategy statistics: chunk count, avg/median/p95 word count, token estimate
  - Chunk size distribution histograms (one per strategy + combined overlay)
  - A summary comparison table printed to stdout
  - Saved as brsr-data/chunks/chunk_analysis.png

Usage:
    python -m chunking.analyze_chunks
    python -m chunking.analyze_chunks --strategies strategy1_row_level strategy3_principle_based
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from utils import CHUNKS_DIR

STRATEGIES = [
    "strategy1_row_level",
    "strategy2_nrow_window",
    "strategy3_principle_based",
    "strategy4_type_aware",
    "strategy5_company_summary",
]

STRATEGY_LABELS = {
    "strategy1_row_level": "S1: Row-level",
    "strategy2_nrow_window": "S2: N-row Window",
    "strategy3_principle_based": "S3: Principle-based",
    "strategy4_type_aware": "S4: Type-aware",
    "strategy5_company_summary": "S5: Company Summary",
}

# Rough approximation: 1 token ≈ 0.75 words (for English text)
WORDS_PER_TOKEN = 0.75


def load_strategy(strategy: str) -> list[dict] | None:
    path = CHUNKS_DIR / strategy / "chunks.jsonl"
    if not path.exists():
        return None
    chunks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def word_count(text: str) -> int:
    return len(text.split())


def compute_stats(chunks: list[dict]) -> dict:
    lengths = [word_count(c["text"]) for c in chunks]
    arr = np.array(lengths, dtype=float)
    return {
        "count": len(chunks),
        "total_words": int(arr.sum()),
        "mean_words": float(arr.mean()),
        "median_words": float(np.median(arr)),
        "p95_words": float(np.percentile(arr, 95)),
        "p99_words": float(np.percentile(arr, 99)),
        "min_words": int(arr.min()),
        "max_words": int(arr.max()),
        "est_mean_tokens": float(arr.mean() / WORDS_PER_TOKEN),
        "lengths": lengths,
    }


def print_table(stats_by_strategy: dict[str, dict]) -> None:
    col_w = 22
    headers = [
        "Strategy",
        "Chunks",
        "Mean words",
        "Median",
        "p95",
        "Max",
        "~Mean tokens",
    ]
    row_fmt = "{:<22} {:>8} {:>11} {:>8} {:>6} {:>6} {:>13}"
    separator = "-" * 80

    print("\n" + separator)
    print("CHUNK ANALYSIS SUMMARY")
    print(separator)
    print(row_fmt.format(*headers))
    print(separator)

    for strategy, stats in stats_by_strategy.items():
        label = STRATEGY_LABELS.get(strategy, strategy)
        print(
            row_fmt.format(
                label[:col_w],
                f"{stats['count']:,}",
                f"{stats['mean_words']:.1f}",
                f"{stats['median_words']:.1f}",
                f"{stats['p95_words']:.1f}",
                f"{stats['max_words']:,}",
                f"{stats['est_mean_tokens']:.1f}",
            )
        )
    print(separator + "\n")


def plot_histograms(stats_by_strategy: dict[str, dict], out_path: Path) -> None:
    n = len(stats_by_strategy)
    if n == 0:
        return

    cols = 2
    rows = (n + 1) // cols + 1  # +1 for overlay plot

    fig, axes = plt.subplots(rows, cols, figsize=(14, rows * 4))
    axes = axes.flatten()

    colors = plt.cm.tab10.colors  # type: ignore[attr-defined]

    # Individual histograms
    for i, (strategy, stats) in enumerate(stats_by_strategy.items()):
        ax = axes[i]
        lengths = stats["lengths"]
        label = STRATEGY_LABELS.get(strategy, strategy)

        # Cap display at p99 to avoid long tail distortion
        cap = stats["p99_words"]
        clipped = [min(l, cap) for l in lengths]

        ax.hist(
            clipped,
            bins=50,
            color=colors[i % len(colors)],
            edgecolor="white",
            linewidth=0.4,
        )
        ax.axvline(
            stats["mean_words"],
            color="red",
            linestyle="--",
            linewidth=1.2,
            label=f"Mean={stats['mean_words']:.0f}",
        )
        ax.axvline(
            stats["median_words"],
            color="orange",
            linestyle=":",
            linewidth=1.2,
            label=f"Median={stats['median_words']:.0f}",
        )
        ax.set_title(label, fontsize=11, fontweight="bold")
        ax.set_xlabel("Words per chunk (capped at p99)")
        ax.set_ylabel("Frequency")
        ax.legend(fontsize=8)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    # Overlay plot (last subplot)
    overlay_ax = axes[n]
    for i, (strategy, stats) in enumerate(stats_by_strategy.items()):
        label = STRATEGY_LABELS.get(strategy, strategy)
        cap = stats["p99_words"]
        clipped = [min(l, cap) for l in stats["lengths"]]
        overlay_ax.hist(
            clipped, bins=50, alpha=0.4, color=colors[i % len(colors)], label=label
        )

    overlay_ax.set_title("All Strategies — Overlay", fontsize=11, fontweight="bold")
    overlay_ax.set_xlabel("Words per chunk (capped at p99)")
    overlay_ax.set_ylabel("Frequency")
    overlay_ax.legend(fontsize=7)
    overlay_ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{int(x):,}")
    )

    # Hide unused axes
    for j in range(n + 1, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(
        "BRSR Chunking Strategy Comparison", fontsize=14, fontweight="bold", y=1.01
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Histogram saved → {out_path}")


def run(strategies: list[str] | None = None) -> None:
    if strategies is None:
        strategies = STRATEGIES

    stats_by_strategy: dict[str, dict] = {}

    for strategy in strategies:
        chunks = load_strategy(strategy)
        if chunks is None:
            print(f"  [skip] {strategy}: chunks.jsonl not found")
            continue
        if not chunks:
            print(f"  [skip] {strategy}: file is empty")
            continue
        stats_by_strategy[strategy] = compute_stats(chunks)
        print(f"  [ok]   {strategy}: {len(chunks):,} chunks loaded")

    if not stats_by_strategy:
        print("No strategy output found. Run the strategy scripts first.")
        return

    print_table(stats_by_strategy)

    out_path = CHUNKS_DIR / "chunk_analysis.png"
    plot_histograms(stats_by_strategy, out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze and compare chunking strategy outputs"
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=None,
        help="Strategy names to analyze (default: all)",
    )
    args = parser.parse_args()
    run(strategies=args.strategies)

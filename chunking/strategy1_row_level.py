"""
Strategy 1 — Row-level (Atomic) Chunking
=========================================
Each non-domain row in the BRSR data becomes one independent chunk.

- Scalar rows  → Q&A text: Metric / Context / Value / Period
- Narrative rows → Disclosure text: Topic / Disclosure / Period

Output: brsr-data/chunks/strategy1_row_level/chunks.jsonl

Usage:
    python -m chunking.strategy1_row_level
    python -m chunking.strategy1_row_level --limit 10   # process only first 10 files
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tqdm import tqdm

from utils import (
    CHUNKS_DIR,
    filter_df,
    grouped_rows_to_text,
    is_narrative_row,
    iter_clean_files,
    map_principle,
    narrative_row_to_text,
    scalar_row_to_text,
    write_jsonl,
)

STRATEGY = "strategy1_row_level"
OUT_DIR = CHUNKS_DIR / STRATEGY


def chunk_file(fp: Path, df) -> list[dict]:
    """Produce one chunk per non-domain row in a company DataFrame."""
    scalar_df, narrative_df = filter_df(df)

    chunks: list[dict] = []

    # --- Scalar rows ---
    for idx, row in enumerate(scalar_df.to_dict("records")):
        principle = map_principle(row["element"])
        text = scalar_row_to_text(row)
        chunks.append(
            {
                "chunk_id": f"s1_{row['symbol']}_{row['fyFrom']}_{row['fyTo']}_sc{idx:04d}",
                "text": text,
                "metadata": {
                    "strategy": STRATEGY,
                    "row_type": "scalar",
                    "symbol": row["symbol"],
                    "companyName": row["companyName"],
                    "fyFrom": row["fyFrom"],
                    "fyTo": row["fyTo"],
                    "element": row["element"],
                    "principle": principle,
                    "period": row.get("period", ""),
                    "source_file": fp.name,
                },
            }
        )

    # --- Narrative rows ---
    for idx, row in enumerate(narrative_df.to_dict("records")):
        principle = map_principle(row["element"])
        text = narrative_row_to_text(row)
        chunks.append(
            {
                "chunk_id": f"s1_{row['symbol']}_{row['fyFrom']}_{row['fyTo']}_nr{idx:04d}",
                "text": text,
                "metadata": {
                    "strategy": STRATEGY,
                    "row_type": "narrative",
                    "symbol": row["symbol"],
                    "companyName": row["companyName"],
                    "fyFrom": row["fyFrom"],
                    "fyTo": row["fyTo"],
                    "element": row["element"],
                    "principle": principle,
                    "period": row.get("period", ""),
                    "source_file": fp.name,
                },
            }
        )

    return chunks


def run(limit: int | None = None) -> None:
    all_chunks: list[dict] = []
    files = list(iter_clean_files())
    if limit:
        files = files[:limit]

    for fp, df in tqdm(files, desc="Strategy 1 — Row-level"):
        all_chunks.extend(chunk_file(fp, df))

    out_path = write_jsonl(all_chunks, OUT_DIR)
    print(f"Written {len(all_chunks):,} chunks → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Strategy 1: row-level chunking")
    parser.add_argument(
        "--limit", type=int, default=None, help="Process only first N files"
    )
    args = parser.parse_args()
    run(limit=args.limit)

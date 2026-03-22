"""
Strategy 2 — N-row Sliding Window Chunking
===========================================
Groups N consecutive non-domain rows within the same company into one chunk,
with a configurable overlap (stride = N - overlap).

Narrative (ExplanatoryTextBlock) rows are kept in the sliding window alongside
scalar rows — they contribute their full text when they fall within a window.

Output: brsr-data/chunks/strategy2_nrow_window/chunks.jsonl

Usage:
    python -m chunking.strategy2_nrow_window
    python -m chunking.strategy2_nrow_window --n 10 --overlap 3
    python -m chunking.strategy2_nrow_window --limit 10
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tqdm import tqdm

from utils import (
    CHUNKS_DIR,
    decamelize,
    filter_df,
    grouped_rows_to_text,
    is_narrative_row,
    iter_clean_files,
    map_principle,
    narrative_row_to_text,
    parse_dimensions,
    write_jsonl,
)

STRATEGY = "strategy2_nrow_window"
OUT_DIR = CHUNKS_DIR / STRATEGY


def _row_inline_text(row: dict) -> str:
    """One-line text representation of a row for use inside a grouped window."""
    if is_narrative_row(row["element"]):
        topic = decamelize(row["element"])
        value = str(row["value"]).strip()
        return f"[Disclosure] {topic}: {value}"

    metric = decamelize(row["element"])
    context = parse_dimensions(str(row.get("dimensions", "") or ""))
    value = str(row["value"]).strip()
    unit = str(row.get("unit", "") or "").strip()

    label = metric
    if context:
        label += f" [{context}]"
    value_str = value
    if unit and unit not in ("nan", ""):
        value_str += f" ({unit})"
    return f"{label}: {value_str}"


def chunk_file(fp: Path, df, n: int, overlap: int) -> list[dict]:
    """Produce sliding-window chunks for one company."""
    scalar_df, narrative_df = filter_df(df)

    # Combine scalar and narrative (preserve original order)
    combined = df[
        ~df["element"].apply(lambda e: e.endswith("Domain") or e.endswith("Member"))
    ].reset_index(drop=True)

    if combined.empty:
        return []

    rows = combined.to_dict("records")
    stride = max(1, n - overlap)

    # Identify company info from first row
    first = rows[0]
    company_name = first["companyName"]
    symbol = first["symbol"]
    fy_from = first["fyFrom"]
    fy_to = first["fyTo"]

    chunks: list[dict] = []
    window_idx = 0
    start = 0

    while start < len(rows):
        window = rows[start : start + n]
        principles_in_window = list(
            dict.fromkeys(map_principle(r["element"]) for r in window)
        )
        dominant_principle = (
            principles_in_window[0]
            if principles_in_window
            else "Section A: General Disclosures"
        )

        header = (
            f"Company: {company_name} ({symbol}) | FY: {fy_from}-{fy_to}"
            f" | Section: {dominant_principle}"
        )
        body_lines = [_row_inline_text(r) for r in window]
        text = header + "\n\n" + "\n".join(body_lines)

        chunks.append(
            {
                "chunk_id": f"s2_{symbol}_{fy_from}_{fy_to}_w{window_idx:05d}",
                "text": text,
                "metadata": {
                    "strategy": STRATEGY,
                    "symbol": symbol,
                    "companyName": company_name,
                    "fyFrom": fy_from,
                    "fyTo": fy_to,
                    "window_start": start,
                    "window_size": len(window),
                    "n": n,
                    "overlap": overlap,
                    "dominant_principle": dominant_principle,
                    "all_principles": principles_in_window,
                    "source_file": fp.name,
                },
            }
        )

        window_idx += 1
        start += stride

    return chunks


def run(n: int = 5, overlap: int = 2, limit: int | None = None) -> None:
    all_chunks: list[dict] = []
    files = list(iter_clean_files())
    if limit:
        files = files[:limit]

    for fp, df in tqdm(files, desc=f"Strategy 2 — N={n} overlap={overlap}"):
        all_chunks.extend(chunk_file(fp, df, n=n, overlap=overlap))

    out_path = write_jsonl(all_chunks, OUT_DIR)
    print(f"Written {len(all_chunks):,} chunks → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Strategy 2: N-row sliding window chunking"
    )
    parser.add_argument("--n", type=int, default=5, help="Window size (default 5)")
    parser.add_argument(
        "--overlap", type=int, default=2, help="Row overlap between windows (default 2)"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Process only first N files"
    )
    args = parser.parse_args()
    run(n=args.n, overlap=args.overlap, limit=args.limit)

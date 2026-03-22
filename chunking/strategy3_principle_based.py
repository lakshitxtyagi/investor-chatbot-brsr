"""
Strategy 3 — BRSR Principle-based (Semantic) Chunking
======================================================
Groups all rows for a (company, BRSR principle/section) pair into one chunk.

Each element is mapped to one of BRSR's 9 Principles or Section A/B using
the `map_principle()` helper in utils.py (explicit PrincipleN tag first,
then keyword heuristics, then Section A fallback).

This is the most semantically coherent strategy — each chunk corresponds
directly to a meaningful BRSR disclosure section, mirroring how analysts
and investors actually read these reports.

Output: brsr-data/chunks/strategy3_principle_based/chunks.jsonl

Usage:
    python -m chunking.strategy3_principle_based
    python -m chunking.strategy3_principle_based --limit 10
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from utils import (
    CHUNKS_DIR,
    decamelize,
    filter_df,
    iter_clean_files,
    map_principle,
    narrative_row_to_text,
    parse_dimensions,
    write_jsonl,
)

STRATEGY = "strategy3_principle_based"
OUT_DIR = CHUNKS_DIR / STRATEGY


def _row_line(row: dict) -> str:
    """Compact single-line representation of a row for grouped chunk body."""
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


def chunk_file(fp: Path, df) -> list[dict]:
    """Produce one chunk per (company, principle) group."""
    scalar_df, narrative_df = filter_df(df)

    if scalar_df.empty and narrative_df.empty:
        return []

    first_row = df[df["symbol"] != ""].iloc[0].to_dict()
    symbol = first_row["symbol"]
    company_name = first_row["companyName"]
    fy_from = first_row["fyFrom"]
    fy_to = first_row["fyTo"]

    # Bucket rows by principle
    buckets: dict[str, list[dict]] = defaultdict(list)

    for row in scalar_df.to_dict("records"):
        principle = map_principle(row["element"])
        buckets[principle].append({"_type": "scalar", **row})

    for row in narrative_df.to_dict("records"):
        principle = map_principle(row["element"])
        buckets[principle].append({"_type": "narrative", **row})

    chunks: list[dict] = []
    for principle, rows in buckets.items():
        header = (
            f"Company: {company_name} ({symbol}) | FY: {fy_from}-{fy_to}"
            f" | Section: {principle}"
        )

        body_lines: list[str] = []
        for row in rows:
            if row["_type"] == "narrative":
                topic = decamelize(row["element"])
                disclosure = str(row["value"]).strip()
                body_lines.append(f"[Disclosure] {topic}:\n{disclosure}")
            else:
                body_lines.append(_row_line(row))

        text = header + "\n\n" + "\n".join(body_lines)

        # Sanitise principle name for use in chunk_id
        principle_slug = (
            principle.lower().replace(" ", "_").replace(":", "").replace("/", "_")
        )

        chunks.append(
            {
                "chunk_id": f"s3_{symbol}_{fy_from}_{fy_to}_{principle_slug}",
                "text": text,
                "metadata": {
                    "strategy": STRATEGY,
                    "symbol": symbol,
                    "companyName": company_name,
                    "fyFrom": fy_from,
                    "fyTo": fy_to,
                    "principle": principle,
                    "row_count": len(rows),
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

    for fp, df in tqdm(files, desc="Strategy 3 — Principle-based"):
        all_chunks.extend(chunk_file(fp, df))

    out_path = write_jsonl(all_chunks, OUT_DIR)
    print(f"Written {len(all_chunks):,} chunks → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Strategy 3: BRSR principle-based chunking"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Process only first N files"
    )
    args = parser.parse_args()
    run(limit=args.limit)

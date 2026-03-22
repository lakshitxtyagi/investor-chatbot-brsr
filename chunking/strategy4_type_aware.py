"""
Strategy 4 — Type-aware (Narrative vs. Numeric) Chunking
=========================================================
Separates rows into two tracks and chunks them differently, addressing the
fundamental heterogeneity in BRSR data:

  Narrative track  — Each ExplanatoryTextBlock row → one standalone chunk.
                     These are already long, self-contained disclosures.

  Numeric track    — Scalar rows grouped by (company, principle) into compact
                     summary chunks (similar to Strategy 3 but numerics-only).

Mixing a 500-word free-text narrative with a 3-character number in the same
embedding would degrade retrieval quality. This strategy keeps them separate
so each chunk type is dense with homogeneous content.

Output: brsr-data/chunks/strategy4_type_aware/chunks.jsonl
        (both tracks written to same file, differentiated by metadata.row_type)

Usage:
    python -m chunking.strategy4_type_aware
    python -m chunking.strategy4_type_aware --limit 10
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

STRATEGY = "strategy4_type_aware"
OUT_DIR = CHUNKS_DIR / STRATEGY


def _scalar_line(row: dict) -> str:
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
    scalar_df, narrative_df = filter_df(df)

    if scalar_df.empty and narrative_df.empty:
        return []

    first_row = df[df["symbol"] != ""].iloc[0].to_dict()
    symbol = first_row["symbol"]
    company_name = first_row["companyName"]
    fy_from = first_row["fyFrom"]
    fy_to = first_row["fyTo"]

    chunks: list[dict] = []

    # ----------------------------------------------------------------
    # Narrative track — one chunk per ExplanatoryTextBlock row
    # ----------------------------------------------------------------
    for idx, row in enumerate(narrative_df.to_dict("records")):
        principle = map_principle(row["element"])
        text = narrative_row_to_text(row)
        chunks.append(
            {
                "chunk_id": f"s4_{symbol}_{fy_from}_{fy_to}_narr{idx:04d}",
                "text": text,
                "metadata": {
                    "strategy": STRATEGY,
                    "row_type": "narrative",
                    "symbol": symbol,
                    "companyName": company_name,
                    "fyFrom": fy_from,
                    "fyTo": fy_to,
                    "element": row["element"],
                    "principle": principle,
                    "period": row.get("period", ""),
                    "source_file": fp.name,
                },
            }
        )

    # ----------------------------------------------------------------
    # Numeric track — group scalar rows by principle
    # ----------------------------------------------------------------
    scalar_buckets: dict[str, list[dict]] = defaultdict(list)
    for row in scalar_df.to_dict("records"):
        principle = map_principle(row["element"])
        scalar_buckets[principle].append(row)

    for principle, rows in scalar_buckets.items():
        header = (
            f"Company: {company_name} ({symbol}) | FY: {fy_from}-{fy_to}"
            f" | Section: {principle} [Numeric Indicators]"
        )
        body_lines = [_scalar_line(r) for r in rows]
        text = header + "\n\n" + "\n".join(body_lines)

        principle_slug = (
            principle.lower().replace(" ", "_").replace(":", "").replace("/", "_")
        )

        chunks.append(
            {
                "chunk_id": f"s4_{symbol}_{fy_from}_{fy_to}_num_{principle_slug}",
                "text": text,
                "metadata": {
                    "strategy": STRATEGY,
                    "row_type": "numeric",
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

    for fp, df in tqdm(files, desc="Strategy 4 — Type-aware"):
        all_chunks.extend(chunk_file(fp, df))

    narrative_count = sum(
        1 for c in all_chunks if c["metadata"]["row_type"] == "narrative"
    )
    numeric_count = sum(1 for c in all_chunks if c["metadata"]["row_type"] == "numeric")

    out_path = write_jsonl(all_chunks, OUT_DIR)
    print(f"Written {len(all_chunks):,} chunks → {out_path}")
    print(f"  Narrative chunks: {narrative_count:,}")
    print(f"  Numeric chunks:   {numeric_count:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Strategy 4: type-aware chunking")
    parser.add_argument(
        "--limit", type=int, default=None, help="Process only first N files"
    )
    args = parser.parse_args()
    run(limit=args.limit)

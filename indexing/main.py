from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tqdm import tqdm

from database_init import get_client, initialize_schema
from embedding import get_brsr_embeddings

DEFAULT_CHUNKS_PATH = Path(__file__).resolve().parent.parent / "brsr-data/chunks/strategy4_type_aware/chunks.jsonl"
NARRATIVE_COLLECTION = "NarrativeCollection"
NUMERICAL_COLLECTION = "NumericalCollection"

# Number of chunks to embed and insert per batch.
BATCH_SIZE = 64


def _to_text(value: Any) -> str:
	if value is None:
		return ""
	return str(value)


def _build_properties(record: dict[str, Any]) -> tuple[dict[str, Any], str]:
	metadata = record.get("metadata") or {}
	row_type = _to_text(metadata.get("row_type", "narrative"))

	properties: dict[str, Any] = {
		"text":        _to_text(record.get("text")),
		"chunk_id":    _to_text(record.get("chunk_id")),
		"companyName": _to_text(metadata.get("companyName")),
		"symbol":      _to_text(metadata.get("symbol")),
		"fyFrom":      _to_text(metadata.get("fyFrom")),
		"fyTo":        _to_text(metadata.get("fyTo")),
		"principle":   _to_text(metadata.get("principle")),
		"element":     _to_text(metadata.get("element")),   # "" for numeric chunks
		"period":      _to_text(metadata.get("period")),    # "" for numeric chunks
		"source_file": _to_text(metadata.get("source_file")),
		"row_type":    row_type,
		"row_count":   int(metadata.get("row_count") or 0), # 0 for narrative chunks
	}
	return properties, row_type


def _load_records(chunks_file: Path, limit: int | None) -> list[dict]:
	"""Load and parse all valid JSONL records from the chunks file."""
	records = []
	with chunks_file.open("r", encoding="utf-8") as f:
		for line_number, line in enumerate(f, start=1):
			if limit is not None and len(records) >= limit:
				break
			payload = line.strip()
			if not payload:
				continue
			try:
				record = json.loads(payload)
			except json.JSONDecodeError:
				print(f"Skipping line {line_number}: invalid JSON")
				continue
			text = _to_text(record.get("text"))
			if not text:
				print(f"Skipping line {line_number}: empty text")
				continue
			records.append(record)
	return records


def embed_and_ingest_chunks(
	chunks_file: Path = DEFAULT_CHUNKS_PATH,
	limit: int | None = None,
) -> None:
	client = get_client()
	try:
		# initialize_schema(client)
		narrative_col = client.collections.get(NARRATIVE_COLLECTION)
		numerical_col = client.collections.get(NUMERICAL_COLLECTION)

		print(f"Loading chunks from {chunks_file} ...")
		records = _load_records(chunks_file, limit)
		print(f"Loaded {len(records):,} valid chunks.")

		inserted = 0
		skipped = 0

		# Process in batches: embed a batch of texts, then insert into Weaviate.
		for batch_start in tqdm(range(0, len(records), BATCH_SIZE), desc="Embedding + ingesting"):
			batch = records[batch_start : batch_start + BATCH_SIZE]
			texts = [_to_text(r.get("text")) for r in batch]

			try:
				vectors = get_brsr_embeddings(texts)
			except Exception as exc:
				print(f"Embedding batch {batch_start}–{batch_start + len(batch)} failed: {exc}")
				skipped += len(batch)
				continue

			for record, vector in zip(batch, vectors):
				properties, row_type = _build_properties(record)
				target_col = numerical_col if row_type == "numeric" else narrative_col
				try:
					target_col.data.insert(
						properties=properties,
						vector={"default": vector},
					)
					inserted += 1
				except Exception as exc:
					skipped += 1
					print(f"Insert failed for chunk {properties.get('chunk_id')!r}: {exc}")

		print(f"Done. Inserted: {inserted:,}, Skipped: {skipped:,}")
	finally:
		client.close()


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Embed BRSR chunks and ingest into Weaviate")
	parser.add_argument(
		"--chunks-file",
		type=Path,
		default=DEFAULT_CHUNKS_PATH,
		help="Path to chunks JSONL file",
	)
	parser.add_argument(
		"--limit",
		type=int,
		default=None,
		help="Optional max number of chunks to ingest",
	)
	return parser.parse_args()


if __name__ == "__main__":
	args = parse_args()
	embed_and_ingest_chunks(chunks_file=args.chunks_file, limit=args.limit)

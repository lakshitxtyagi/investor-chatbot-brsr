import argparse
import json
from pathlib import Path
from typing import Any

from database_init import client, initialize_schema
from embedding import get_brsr_embedding


DEFAULT_CHUNKS_PATH = Path("brsr-data/chunks/strategy4_type_aware/chunks.jsonl")
NARRATIVE_COLLECTION = "NarrativeCollection"
NUMERICAL_COLLECTION = "NumericalCollection"


def _to_text(value: Any) -> str:
	if value is None:
		return ""
	return str(value)


def _collection_name(row_type: str) -> str:
	if row_type.strip().lower() == "numeric":
		return NUMERICAL_COLLECTION
	return NARRATIVE_COLLECTION


def _build_properties(record: dict[str, Any]) -> tuple[dict[str, str], str]:
	metadata = record.get("metadata") or {}
	row_type = _to_text(metadata.get("row_type", "narrative"))

	properties = {
		"text": _to_text(record.get("text")),
		"chunk_id": _to_text(record.get("chunk_id")),
		"companyName": _to_text(metadata.get("companyName")),
		"symbol": _to_text(metadata.get("symbol")),
		"fyFrom": _to_text(metadata.get("fyFrom")),
		"fyTo": _to_text(metadata.get("fyTo")),
		"principle": _to_text(metadata.get("principle")),
		"element": _to_text(metadata.get("element")),
		"period": _to_text(metadata.get("period")),
		"source_file": _to_text(metadata.get("source_file")),
		"row_type": row_type,
	}
	return properties, row_type


def embed_and_ingest_chunks(
	chunks_file: Path = DEFAULT_CHUNKS_PATH,
	limit: int | None = None,
) -> None:
	initialize_schema(client)

	narrative = client.collections.get(NARRATIVE_COLLECTION)
	numerical = client.collections.get(NUMERICAL_COLLECTION)

	inserted = 0
	skipped = 0

	with chunks_file.open("r", encoding="utf-8") as f:
		for line_number, line in enumerate(f, start=1):
			if limit is not None and inserted >= limit:
				break

			payload = line.strip()
			if not payload:
				continue

			try:
				record = json.loads(payload)
			except json.JSONDecodeError:
				skipped += 1
				print(f"Skipping line {line_number}: invalid JSON")
				continue

			properties, row_type = _build_properties(record)
			text = properties["text"]
			if not text:
				skipped += 1
				continue

			try:
				vector = get_brsr_embedding(text)
				target_collection = numerical if _collection_name(row_type) == NUMERICAL_COLLECTION else narrative
				target_collection.data.insert(properties=properties, vector=vector)
				inserted += 1
			except Exception as exc:  # noqa: BLE001
				skipped += 1
				print(f"Skipping line {line_number}: {exc}")

	print(f"Done. Inserted: {inserted}, Skipped: {skipped}")


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

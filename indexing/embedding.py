import os
from typing import Iterable

from google import genai


DEFAULT_EMBED_MODEL = "gemini-embedding-001"


def get_genai_client(api_key: str | None = None) -> genai.Client:
	"""Return a configured Gemini client.

	If ``api_key`` is not provided, the function falls back to the
	``GEMINI_API_KEY`` or ``GOOGLE_API_KEY`` environment variables.
	"""
	resolved_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
	if resolved_key:
		return genai.Client(api_key=resolved_key)
	return genai.Client()


def get_brsr_embedding(
	text: str,
	model: str = DEFAULT_EMBED_MODEL,
	api_key: str | None = None,
	client: genai.Client | None = None,
) -> list[float]:
	"""Generate a single embedding vector for a BRSR text chunk."""
	if not text or not text.strip():
		raise ValueError("text must be a non-empty string")

	active_client = client or get_genai_client(api_key=api_key)
	result = active_client.models.embed_content(model=model, contents=text)
	return list(result.embeddings[0].values)


def get_brsr_embeddings(
	texts: Iterable[str],
	model: str = DEFAULT_EMBED_MODEL,
	api_key: str | None = None,
	client: genai.Client | None = None,
) -> list[list[float]]:
	"""Generate embedding vectors for multiple BRSR text chunks."""
	cleaned_texts = [t.strip() for t in texts if t and t.strip()]
	if not cleaned_texts:
		return []

	active_client = client or get_genai_client(api_key=api_key)
	result = active_client.models.embed_content(model=model, contents=cleaned_texts)
	return [list(embedding.values) for embedding in result.embeddings]


__all__ = [
	"DEFAULT_EMBED_MODEL",
	"get_genai_client",
	"get_brsr_embedding",
	"get_brsr_embeddings",
]

from __future__ import annotations

from typing import Iterable

import torch
from sentence_transformers import SentenceTransformer


DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Prefer Apple Silicon GPU (MPS), fall back to CPU.
_DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

# Module-level singleton – downloaded once and cached by sentence-transformers.
_model: SentenceTransformer | None = None


def _get_model(model_name: str = DEFAULT_EMBED_MODEL) -> SentenceTransformer:
    global _model
    if _model is None or _model.device.type != _DEVICE:
        _model = SentenceTransformer(model_name, device=_DEVICE)
    return _model


def get_brsr_embedding(
    text: str,
    model: str = DEFAULT_EMBED_MODEL,
) -> list[float]:
    """Generate a single embedding vector for a BRSR text chunk."""
    if not text or not text.strip():
        raise ValueError("text must be a non-empty string")

    st_model = _get_model(model)
    vector = st_model.encode(text.strip(), convert_to_numpy=True)
    return vector.tolist()


def get_brsr_embeddings(
    texts: Iterable[str],
    model: str = DEFAULT_EMBED_MODEL,
) -> list[list[float]]:
    """Generate embedding vectors for multiple BRSR text chunks."""
    cleaned = [t.strip() for t in texts if t and t.strip()]
    if not cleaned:
        return []

    st_model = _get_model(model)
    vectors = st_model.encode(cleaned, convert_to_numpy=True, batch_size=64, show_progress_bar=True)
    return [v.tolist() for v in vectors]


__all__ = [
    "DEFAULT_EMBED_MODEL",
    "get_brsr_embedding",
    "get_brsr_embeddings",
]

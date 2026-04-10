"""
rag.py — Core RAG pipeline
==========================
1. Embed the user query with sentence-transformers/all-MiniLM-L6-v2
2. Retrieve top-k chunks from each requested Weaviate collection via
   near_vector search
3. Build a context string and call Gemini 2.5 Flash Lite
4. Return structured response
"""

from __future__ import annotations

import os

from google import genai
import weaviate
from sentence_transformers import SentenceTransformer

from config import settings

# ---------------------------------------------------------------------------
# Singletons — loaded once at import time
# ---------------------------------------------------------------------------

_embedder: SentenceTransformer | None = None
_weaviate_client: weaviate.WeaviateClient | None = None
_collection_name_map: dict[str, str] | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        local_model_path = settings.EMBEDDING_MODEL_PATH
        if os.path.isdir(local_model_path):
            print(f"[RAG] Loading embedding model from local path: {local_model_path}")
            _embedder = SentenceTransformer(local_model_path)
        else:
            print(f"[RAG] Loading embedding model: {settings.EMBEDDING_MODEL}")
            _embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedder


def get_weaviate_client() -> weaviate.WeaviateClient:
    global _weaviate_client
    if _weaviate_client is None or not _weaviate_client.is_connected():
        print(f"[RAG] Connecting to Weaviate at {settings.WEAVIATE_URL}")
        _weaviate_client = weaviate.connect_to_custom(
            http_host=settings.WEAVIATE_HOST,
            http_port=settings.WEAVIATE_PORT,
            http_secure=False,
            grpc_host=settings.WEAVIATE_HOST,
            grpc_port=settings.WEAVIATE_GRPC_PORT,
            grpc_secure=False,
            auth_credentials=weaviate.auth.AuthApiKey(settings.WEAVIATE_API_KEY),
        )
    return _weaviate_client


def resolve_collection_name(client: weaviate.WeaviateClient, requested: str) -> str:
    """Resolve requested collection name to the exact schema name (case-insensitive)."""
    global _collection_name_map

    if _collection_name_map is None:
        _collection_name_map = {}
        try:
            collections = client.collections.list_all()
            _collection_name_map = {
                name.lower(): name for name in collections.keys()
            }
        except Exception as exc:
            print(f"[RAG] Could not list collections for name resolution: {exc}")

    return _collection_name_map.get(requested.lower(), requested)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve_chunks(
    query_vector: list[float],
    collection_name: str,
    top_k: int,
) -> list[dict]:
    """Return top_k objects from a Weaviate collection via near_vector search."""
    client = get_weaviate_client()
    resolved_collection_name = resolve_collection_name(client, collection_name)

    try:
        collection = client.collections.get(resolved_collection_name)
    except Exception as exc:
        print(
            f"[RAG] Could not access collection '{collection_name}' "
            f"(resolved as '{resolved_collection_name}'): {exc}"
        )
        return []

    try:
        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=top_k,
            return_metadata=["distance"],
        )
    except Exception as exc:
        print(
            f"[RAG] near_vector query failed on '{collection_name}' "
            f"(resolved as '{resolved_collection_name}'): {exc}"
        )
        return []

    chunks = []
    for obj in response.objects:
        props = obj.properties or {}
        distance = obj.metadata.distance if obj.metadata else 1.0
        score = round(1.0 - float(distance), 4)  # cosine similarity proxy

        chunks.append(
            {
                "chunk_id": props.get("chunk_id", str(obj.uuid)),
                "text": props.get("text", ""),
                "collection": resolved_collection_name,
                "score": score,
                "metadata": {
                    k: v
                    for k, v in props.items()
                    if k not in ("chunk_id", "text")
                },
            }
        )

    return chunks


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        meta_str = ", ".join(
            f"{k}={v}"
            for k, v in c["metadata"].items()
            if v and k not in ("strategy", "source_file")
        )
        parts.append(
            f"[{i}] Collection: {c['collection']} | {meta_str}\n{c['text']}"
        )
    return "\n\n---\n\n".join(parts)


def call_gemini(query: str, context: str) -> str:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    prompt = f"""You are an expert analyst for Business Responsibility and Sustainability Reports (BRSR).
Use ONLY the retrieved context below to answer the user's question.
If the context does not contain enough information, say so clearly.
Be precise, cite company names and financial years when available.

=== RETRIEVED CONTEXT ===
{context}

=== USER QUESTION ===
{query}

=== ANSWER ==="""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    return response.text.strip()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def execute_rag(
    query: str,
    top_k: int = 5,
    collections: list[str] | None = None,
) -> dict:
    if collections is None:
        collections = settings.DEFAULT_COLLECTIONS

    # 1. Embed query
    embedder = get_embedder()
    query_vector: list[float] = embedder.encode(query).tolist()

    # 2. Retrieve from each collection
    all_chunks: list[dict] = []
    for col in collections:
        chunks = retrieve_chunks(query_vector, col, top_k)
        all_chunks.extend(chunks)

    # 3. Re-rank by score descending, keep top_k * len(collections)
    all_chunks.sort(key=lambda x: x["score"], reverse=True)
    top_chunks = all_chunks[: top_k * len(collections)]

    # 4. Generate answer
    if top_chunks:
        context = build_context(top_chunks)
        answer = call_gemini(query, context)
    else:
        answer = "No relevant information found in the database for your query."

    return {
        "query": query,
        "answer": answer,
        "sources": top_chunks,
        "total_chunks_retrieved": len(top_chunks),
    }
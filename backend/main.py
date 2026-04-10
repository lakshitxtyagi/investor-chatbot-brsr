"""
FastAPI RAG Backend
===================
Exposes POST /execute — takes a user query, retrieves relevant chunks
from Weaviate (narrativecollection + numericalcollection), and generates
an answer using Gemini 2.5 Flash Lite.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag import execute_rag

app = FastAPI(
    title="BRSR RAG API",
    description="RAG over BRSR embeddings stored in Weaviate",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5                     # chunks retrieved per collection
    collections: list[str] | None = None  # None → both; or ["narrativecollection"]


class SourceChunk(BaseModel):
    chunk_id: str
    text: str
    collection: str
    score: float
    metadata: dict


class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: list[SourceChunk]
    total_chunks_retrieved: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/execute", response_model=QueryResponse)
async def execute(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    result = await execute_rag(
        query=request.query,
        top_k=request.top_k,
        collections=request.collections,
    )
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
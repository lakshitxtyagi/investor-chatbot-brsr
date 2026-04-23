"""
FastAPI RAG Backend
===================
Exposes:
  POST /execute        — standard RAG Q&A
  POST /due-diligence  — multi-section due diligence report agent
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag import execute_rag
from due_diligence import execute_due_diligence

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


class DueDiligenceRequest(BaseModel):
    company: str
    symbol: str | None = None  # if provided, scopes Weaviate queries to this symbol


class SectionResult(BaseModel):
    title: str
    chunk_count: int
    sources: list[SourceChunk]


class DueDiligenceResponse(BaseModel):
    company: str
    symbol: str | None = None
    report_markdown: str
    sections: list[SectionResult]
    total_sources: int


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


@app.post("/due-diligence", response_model=DueDiligenceResponse)
async def due_diligence(request: DueDiligenceRequest):
    if not request.company.strip():
        raise HTTPException(status_code=400, detail="company must not be empty")

    result = await execute_due_diligence(
        company=request.company.strip(),
        symbol=request.symbol.strip().upper() if request.symbol else None,
    )
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
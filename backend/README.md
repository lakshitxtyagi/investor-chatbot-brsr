# BRSR RAG Backend

FastAPI backend that serves a RAG pipeline over BRSR embeddings stored in Weaviate.

## Stack

| Layer | Tech |
|---|---|
| API | FastAPI + Uvicorn |
| Vector DB | Weaviate 1.36.6 (your running Docker container) |
| Embedder | `sentence-transformers/all-MiniLM-L6-v2` |
| LLM | Gemini 2.5 Flash Lite |

---

## Setup

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

### 3. Make sure Weaviate is running

```bash
docker compose up -d   # from the folder with your docker-compose.yml
```

### 4. Start the API server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## API Reference

### `GET /health`
Returns `{"status": "ok"}`.

---

### `POST /execute`

Run a RAG query against the BRSR database.

**Request body**

```json
{
  "query": "What is Infosys water consumption in FY2023?",
  "top_k": 5,
  "collections": ["narrativecollection", "numericalcollection"]
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `query` | string | required | Natural language question |
| `top_k` | int | 5 | Chunks retrieved per collection |
| `collections` | list[str] | both | Which collections to search |

**Response**

```json
{
  "query": "What is Infosys water consumption in FY2023?",
  "answer": "According to the retrieved data, Infosys reported...",
  "sources": [
    {
      "chunk_id": "s4_INFY_2022_2023_num_water",
      "text": "Company: Infosys (INFY) | FY: 2022-2023 ...",
      "collection": "numericalcollection",
      "score": 0.91,
      "metadata": { "symbol": "INFY", "fyFrom": "2022", ... }
    }
  ],
  "total_chunks_retrieved": 8
}
```

---

## Project Structure

```
backend/
├── main.py          # FastAPI app + endpoint definitions
├── rag.py           # Embed → Retrieve → Generate pipeline
├── config.py        # All settings (env-driven via pydantic-settings)
├── requirements.txt
├── .env.example     # Template — copy to .env
└── README.md
```

---

## Customisation Tips

- **Change top_k** — pass `"top_k": 10` in the request body.
- **Search only narrative** — pass `"collections": ["narrativecollection"]`.
- **Swap LLM** — change `GEMINI_MODEL` in `.env`.
- **Add auth** — wrap `execute()` with a FastAPI `Depends` bearer-token check.
# Backend Setup

## 1. Install dependencies

From the project root:

```bash
pip install -r requirements.txt
```

## 2. Configure environment variables

Create or update `backend/.env` and set:

```env
GEMINI_API_KEY=your_api_key_here
```

## 3. Initialize the local embedding model

Run this command from the `backend` folder so the model is saved to `backend/model`:

```bash
cd backend
python __init_model__.py
```

## 4. Start the backend

From the `backend` folder:

```bash
python main.py
```

## Quick check

Test the API from another terminal:

```bash
curl -X POST http://localhost:8000/execute \
	-H "Content-Type: application/json" \
	-d '{"query": "What are the water consumption metrics for FY2023?"}'
```

## Troubleshooting

- If local model loading fails, re-run `python __init_model__.py` from `backend`.
- Ensure `backend/model` contains files like `modules.json` and `config_sentence_transformers.json`.
- Verify `GEMINI_API_KEY` is present in `backend/.env`.
# backend/download_model.py
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
SAVE_PATH = "./model"

print(f"Downloading {MODEL_NAME} → {SAVE_PATH}")
model = SentenceTransformer(MODEL_NAME)
model.save(SAVE_PATH)
print("Done.")
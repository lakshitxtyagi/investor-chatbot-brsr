import weaviate
from weaviate.classes.init import Auth

# Replace with your details
WEAVIATE_URL = "http://localhost:8080"
WEAVIATE_API_KEY = "user-a-key"

def get_client():
    return weaviate.connect_to_local(
        port=8080,
        grpc_port=50051,
        auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
    )


# Exported client instance for reuse in data ingestion scripts.
client = get_client()

properties = [
    {"name": "text", "dataType": ["text"]},
    {"name": "chunk_id", "dataType": ["text"]},
    {"name": "companyName", "dataType": ["text"]},
    {"name": "symbol", "dataType": ["text"]},
    {"name": "fyFrom", "dataType": ["text"]},
    {"name": "fyTo", "dataType": ["text"]},
    {"name": "principle", "dataType": ["text"]},
    {"name": "element", "dataType": ["text"]},
    {"name": "period", "dataType": ["text"]},
    {"name": "source_file", "dataType": ["text"]},
    {"name": "row_type", "dataType": ["text"]},
]

narrative_class = {
    "class": "NarrativeCollection",
    "description": "Stores narrative ESG chunks",
    "vectorizer": "none",  # IMPORTANT: we provide embeddings
    "properties": properties,
}

# -------------------------------
# Numerical Collection
# -------------------------------
numerical_class = {
    "class": "NumericalCollection",
    "description": "Stores numerical/scalar ESG chunks",
    "vectorizer": "none",
    "properties": properties,
}

def initialize_schema(db_client=None):
    db_client = db_client or client

    # Test connection
    if db_client.is_live():
        print("✅ Connected to Weaviate with API key!")
    else:
        print("❌ Connection failed")
        return

    # Create classes only if they do not already exist.
    existing = {cls["class"] for cls in db_client.schema.get().get("classes", [])}

    if narrative_class["class"] not in existing:
        db_client.schema.create_class(narrative_class)
    if numerical_class["class"] not in existing:
        db_client.schema.create_class(numerical_class)

    print("✅ Weaviate schema initialized successfully!")


__all__ = ["client", "get_client", "initialize_schema"]


if __name__ == "__main__":
    initialize_schema()


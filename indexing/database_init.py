from __future__ import annotations

import weaviate
import weaviate.classes.config as wvc
from weaviate.classes.init import Auth

WEAVIATE_HOST = "localhost"
WEAVIATE_PORT = 8083
WEAVIATE_GRPC_PORT = 50051
WEAVIATE_API_KEY = "user-a-key"

NARRATIVE_COLLECTION = "NarrativeCollection"
NUMERICAL_COLLECTION = "NumericalCollection"

_PROPERTIES = [
    wvc.Property(name="text",        data_type=wvc.DataType.TEXT),
    wvc.Property(name="chunk_id",    data_type=wvc.DataType.TEXT),
    wvc.Property(name="companyName", data_type=wvc.DataType.TEXT),
    wvc.Property(name="symbol",      data_type=wvc.DataType.TEXT),
    wvc.Property(name="fyFrom",      data_type=wvc.DataType.TEXT),
    wvc.Property(name="fyTo",        data_type=wvc.DataType.TEXT),
    wvc.Property(name="principle",   data_type=wvc.DataType.TEXT),
    wvc.Property(name="element",     data_type=wvc.DataType.TEXT),  # narrative only; "" for numeric
    wvc.Property(name="period",      data_type=wvc.DataType.TEXT),  # narrative only; "" for numeric
    wvc.Property(name="source_file", data_type=wvc.DataType.TEXT),
    wvc.Property(name="row_type",    data_type=wvc.DataType.TEXT),
    wvc.Property(name="row_count",   data_type=wvc.DataType.INT),   # numeric only; 0 for narrative
]


def get_client() -> weaviate.WeaviateClient:
    return weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=WEAVIATE_PORT,
        grpc_port=WEAVIATE_GRPC_PORT,
        auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
    )


def initialize_schema(db_client: weaviate.WeaviateClient) -> None:
    if db_client.is_live():
        print("✅ Connected to Weaviate!")
    else:
        print("❌ Connection failed")
        return

    existing = set(db_client.collections.list_all().keys())

    if NARRATIVE_COLLECTION not in existing:
        db_client.collections.create(
            name=NARRATIVE_COLLECTION,
            description="Stores narrative ESG chunks",
            # self_provided = we supply our own vectors at insert time
            vector_config=wvc.Configure.Vectors.self_provided(),
            properties=_PROPERTIES,
        )

    if NUMERICAL_COLLECTION not in existing:
        db_client.collections.create(
            name=NUMERICAL_COLLECTION,
            description="Stores numerical/scalar ESG chunks",
            vector_config=wvc.Configure.Vectors.self_provided(),
            properties=_PROPERTIES,
        )

    print("✅ Weaviate schema initialized successfully!")


__all__ = ["get_client", "initialize_schema"]


if __name__ == "__main__":
    _client = get_client()
    try:
        initialize_schema(_client)
    finally:
        _client.close()

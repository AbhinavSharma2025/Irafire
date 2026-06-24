import json
from pathlib import Path
from typing import Any

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models

from config import (
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    OPENAI_API_KEY,
    QDRANT_HOST,
    QDRANT_PORT,
)


def _get_openai_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=OPENAI_API_KEY)


def _get_qdrant_client() -> QdrantClient:
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def _ensure_collection(client: QdrantClient, vector_size: int) -> None:
    collections = client.get_collections().collections
    collection_names = {collection.name for collection in collections}

    if COLLECTION_NAME not in collection_names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )


def embed_rules(rules_path: str) -> int:
    """Embed NBC rules and upsert them into the Qdrant collection."""
    rules_file = Path(rules_path)
    if not rules_file.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")

    with rules_file.open("r", encoding="utf-8") as f:
        rules: list[dict[str, Any]] = json.load(f)

    if not rules:
        return 0

    texts = [f"{rule['rule']}\nReference: {rule['reference']}" for rule in rules]

    openai_client = _get_openai_client()
    embedding_response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )

    vectors = [item.embedding for item in embedding_response.data]

    qdrant_client = _get_qdrant_client()
    _ensure_collection(qdrant_client, vector_size=len(vectors[0]))

    # ✅ FIX: use enumerate index as integer ID, keep NBC_001 in payload
    points = []
    for idx, (rule, vector) in enumerate(zip(rules, vectors)):
        payload = {
            "id": rule["id"],
            "category": rule["category"],
            "rule": rule["rule"],
            "reference": rule["reference"],
        }
        points.append(
            models.PointStruct(
                id=idx,        # ✅ integer, not "NBC_001"
                vector=vector,
                payload=payload,
            )
        )

    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    return len(points)


def search_rules(
    query: str,
    category_filter: str = None,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Search NBC rules semantically and optionally filter by category."""
    if not query or not query.strip():
        return []

    openai_client = _get_openai_client()
    query_embedding = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query,
    ).data[0].embedding

    qdrant_client = _get_qdrant_client()

    query_filter = None
    if category_filter:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="category",
                    match=models.MatchValue(value=category_filter),
                )
            ]
        )

    results = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
    )

    matches: list[dict[str, Any]] = []
    for item in results:
        payload = item.payload or {}
        matches.append(
            {
                "id": payload.get("id"),
                "category": payload.get("category"),
                "rule": payload.get("rule"),
                "reference": payload.get("reference"),
                "score": item.score,
            }
        )

    return matches


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    default_rules_path = project_root / "knowledge_base" / "nbc_rules.json"
    total = embed_rules(str(default_rules_path))
    print(f"✅ Embedded and upserted {total} rules into collection '{COLLECTION_NAME}'.")
import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "nbc_fire_rules"
MODEL_NAME = "gpt-4o-mini"  # cheaper than gpt-4o, still very capable
EMBEDDING_MODEL = "text-embedding-3-small"  # cheapest embedding model
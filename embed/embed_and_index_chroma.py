import os
import json
import chromadb
from chromadb import PersistentClient
from chromadb.utils import embedding_functions

# Paths
PASSAGES_FILE = r"C:\news-chatbot\backend\data\processed\passages.jsonl"
PERSIST_DIR = r"C:\news-chatbot\backend\data\processed\chroma_db"

# 1) Load passages
print(f"Loading passages from {PASSAGES_FILE}")
try:
    records = [json.loads(line) for line in open(PASSAGES_FILE, "r", encoding="utf-8")]
    texts = [r["text"] for r in records]
    ids = [r["id"] for r in records]
    print(f"Loaded {len(records)} passages")
    # Validate data
    empty_texts = [i for i, t in enumerate(texts) if not t or not isinstance(t, str)]
    if empty_texts:
        print(f"Warning: Found {len(empty_texts)} empty or invalid texts at indices: {empty_texts}")
    duplicate_ids = [id for id in set(ids) if ids.count(id) > 1]
    if duplicate_ids:
        print(f"Error: Found duplicate IDs: {duplicate_ids}")
        exit(1)
except FileNotFoundError:
    print(f"Error: {PASSAGES_FILE} not found")
    exit(1)
except Exception as e:
    print(f"Error loading passages: {e}")
    exit(1)

# 2) Initialize Chroma client
print(f"Initializing Chroma DB at {PERSIST_DIR}")
try:
    client = PersistentClient(path=PERSIST_DIR)
except Exception as e:
    print(f"Error initializing Chroma client: {e}")
    exit(1)

# 3) Creating  a collection
collection_name = "news_passages"
if collection_name in [c.name for c in client.list_collections()]:
    print(f"Collection '{collection_name}' exists. Deleting…")
    client.delete_collection(name=collection_name)

print(f"Creating Chroma collection '{collection_name}'")
try:
    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
    )
    print(f"Collection created: {collection}")
except Exception as e:
    print(f"Error creating collection: {e}")
    exit(1)

# 4) Upserting all passages
print(f"Upserting {len(texts)} passages")
try:
    collection.add(
        documents=texts,
        metadatas=[{"source": r["source"], "pub": r["published"]} for r in records],
        ids=ids
    )
    print("Upsert completed successfully")
    # Verify collection contents
    count = collection.count()
    print(f"Documents in collection after upsert: {count}")
    if count != len(texts):
        print(f"Warning: Expected {len(texts)} documents, but found {count}")
except Exception as e:
    print(f"Error upserting passages: {e}")
    exit(1)

print("✅ Done. Your passages are now indexed in Chroma.")
import chromadb
import os

# Set the path to ChromaDB
PERSIST_DIR = r"C:\news-chatbot\backend\data\processed\chroma_db"

# Initialize ChromaDB client
client = chromadb.PersistentClient(path=PERSIST_DIR)
collection = client.get_collection("news_passages")

# Print document count
print(f"Number of documents in collection: {collection.count()}")
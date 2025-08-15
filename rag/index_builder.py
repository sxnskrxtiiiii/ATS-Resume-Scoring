import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from datetime import datetime
import os

KB_PATH = os.path.join("rag", "all.json")
INDEX_PATH = os.path.join("rag", "faiss.index")
IDS_PATH = os.path.join("rag", "ids.json")

def load_kb():
    with open(KB_PATH, "r", encoding="utf-8") as f:
        docs = json.load(f)
    return docs

def build_index():
    # Load KB
    docs = load_kb()
    texts = [d["text"] for d in docs]
    ids = [d["id"] for d in docs]

    # Load embedding model
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    # Create FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product = cosine (since normalized)
    index.add(embeddings)

    # Save index & ids
    faiss.write_index(index, INDEX_PATH)
    with open(IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(ids, f, indent=2)

    print(f"[{datetime.now()}] Indexed {len(ids)} KB entries")
    print(f"Index saved to: {INDEX_PATH}")
    print(f"IDs saved to: {IDS_PATH}")

if __name__ == "__main__":
    build_index()

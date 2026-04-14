import os
import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = chromadb.PersistentClient(path="./chroma_db")
col = client.get_or_create_collection("day09_docs")

# OpenAI Implementation
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

docs_dir = "./data/docs"

for fname in os.listdir(docs_dir):
    fpath = os.path.join(docs_dir, fname)

    if not os.path.isfile(fpath):
        continue

    try:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

    # Get OpenAI embedding
    resp = openai_client.embeddings.create(input=content, model="text-embedding-3-small")
    embedding = resp.data[0].embedding

    col.upsert(
        ids=[fname],
        documents=[content],
        embeddings=[embedding],
        metadatas=[{"source": fname}]
    )

    print(f"Indexed: {fname}")

print("Index ready.")
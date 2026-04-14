# import chromadb, os
# from sentence_transformers import SentenceTransformer
#
# client = chromadb.PersistentClient(path='./chroma_db')
# col = client.get_or_create_collection('day09_docs')
# model = SentenceTransformer('all-MiniLM-L6-v2')
#
# docs_dir = './data/docs'
# for fname in os.listdir(docs_dir):
#     with open(os.path.join(docs_dir, fname), 'r', encoding='utf-8') as f:
#         content = f.read()
#     print(f'Indexed: {fname}')
# print('Index ready.')
#
# print("Count:", col.count())  # Nếu 0 → chưa index
# print("Peek:", col.peek())    # Xem vài record đầu

#####################################################

# index_docs.py — chạy 1 lần để build ChromaDB
import os, chromadb
from openai import OpenAI
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma = chromadb.PersistentClient(path="./chroma_db")
collection = chroma.get_or_create_collection(
    "day09_docs",
    metadata={"hnsw:space": "cosine"}
)

txt_dir = "./data/docs"  # ← sửa đúng đường dẫn folder .txt của bạn
for fname in os.listdir(txt_dir):
    if not fname.endswith(".txt"):
        continue
    fpath = os.path.join(txt_dir, fname)
    text = open(fpath, encoding="utf-8").read()

    # Chunk đơn giản theo đoạn (hoặc fixed-size)
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]

    for i, chunk in enumerate(chunks):
        embedding = client.embeddings.create(
            input=chunk,
            model="text-embedding-3-small"
        ).data[0].embedding

        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"{fname}_chunk_{i}"],
            metadatas=[{"source": fname}]
        )
    print(f"Indexed {len(chunks)} chunks from {fname}")

print("Done! Total:", collection.count())
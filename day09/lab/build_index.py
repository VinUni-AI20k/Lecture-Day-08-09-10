"""
Build ChromaDB index for Day 09 Lab using OpenAI embeddings
"""
import chromadb
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Building ChromaDB index with OpenAI embeddings...")

# Initialize OpenAI client
client_openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize ChromaDB with OpenAI embedding function
from chromadb.utils import embedding_functions

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv('OPENAI_API_KEY'),
    model_name="text-embedding-3-small"
)

# Initialize ChromaDB
client = chromadb.PersistentClient(path='./chroma_db')
collection = client.get_or_create_collection(
    name='day09_docs',
    embedding_function=openai_ef
)

# Read and index documents
docs_dir = Path('./data/docs')
documents = []
metadatas = []
ids = []

for idx, doc_file in enumerate(sorted(docs_dir.glob('*.txt'))):
    with open(doc_file, encoding='utf-8') as f:
        content = f.read()
    
    # Simple chunking by paragraphs
    chunks = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    for chunk_idx, chunk in enumerate(chunks):
        if len(chunk) > 50:  # Skip very short chunks
            documents.append(chunk)
            metadatas.append({
                'source': doc_file.name,
                'chunk_id': f"{doc_file.stem}_{chunk_idx}"
            })
            ids.append(f"{doc_file.stem}_{chunk_idx}")
    
    print(f"✓ Indexed: {doc_file.name} ({len(chunks)} chunks)")

# Add to collection
if documents:
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"\n✅ Index built successfully!")
    print(f"   Total chunks: {len(documents)}")
    print(f"   Collection: {collection.name}")
else:
    print("❌ No documents found!")

# Test query
print("\n🔍 Testing index with sample query...")
results = collection.query(
    query_texts=["SLA P1 ticket"],
    n_results=3
)
print(f"   Found {len(results['documents'][0])} results")
for i, doc in enumerate(results['documents'][0][:2]):
    print(f"   {i+1}. {doc[:80]}...")

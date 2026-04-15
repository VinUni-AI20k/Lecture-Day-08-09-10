"""
chat_box.py — Simple CLI chat over Day 08 RAG index

Usage:
  python chat_box.py

Type 'exit' to quit.
"""

import os
import re
from typing import List, Dict, Any

import chromadb
from dotenv import load_dotenv

from index import CHROMA_DB_DIR, COLLECTION_NAME, DOCS_DIR, preprocess_document, get_embedding

load_dotenv()

TOP_K = 3
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def retrieve_keyword_fallback(query: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
    q_tokens = set(_tokenize(query))
    scored: List[Dict[str, Any]] = []

    for path in sorted(DOCS_DIR.glob("*.txt")):
        raw = path.read_text(encoding="utf-8")
        doc = preprocess_document(raw, str(path))
        text = doc.get("text", "")
        d_tokens = set(_tokenize(text))
        overlap = len(q_tokens & d_tokens)

        if overlap <= 0:
            continue

        scored.append(
            {
                "text": text[:1800],
                "metadata": {
                    "source": doc.get("metadata", {}).get("source", path.name),
                    "section": "keyword_fallback",
                    "effective_date": doc.get("metadata", {}).get("effective_date", "unknown"),
                },
                "score": float(overlap),
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def retrieve(query: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection(COLLECTION_NAME)

    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    chunks: List[Dict[str, Any]] = []
    for doc, meta, dist in zip(docs, metas, dists):
        score = 1 - dist if dist is not None else 0
        chunks.append({"text": doc, "metadata": meta, "score": score})

    return chunks


def build_context(chunks: List[Dict[str, Any]]) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        m = c.get("metadata", {})
        source = m.get("source", "unknown")
        section = m.get("section", "")
        score = c.get("score", 0)

        header = f"[{i}] {source}"
        if section:
            header += f" | {section}"
        header += f" | score={score:.2f}"

        blocks.append(f"{header}\n{c.get('text', '')}")

    return "\n\n".join(blocks)


def call_llm(prompt: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()

    if provider == "openai":
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing")

        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=400,
        )
        return (resp.choices[0].message.content or "").strip()

    if provider == "gemini":
        import google.generativeai as genai

        api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is missing")

        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()

    raise ValueError("LLM_PROVIDER must be 'openai' or 'gemini'")


def answer(query: str) -> Dict[str, Any]:
    retrieval_notice = ""
    try:
        chunks = retrieve(query)
    except Exception as e:
        chunks = retrieve_keyword_fallback(query)
        retrieval_notice = f"[Retrieve fallback] {e}"

    context = build_context(chunks)

    prompt = f"""Answer only from the retrieved context below.
If the context is insufficient, say: Khong du du lieu trong tai lieu hien co.
Cite sources like [1], [2] when possible.
Keep the answer concise.

Question: {query}

Context:
{context}

Answer:"""

    try:
        text = call_llm(prompt)
    except Exception as e:
        # Fallback when API is unavailable: still show top contexts.
        text = f"Khong goi duoc LLM ({e}). Vui long xem context retrieve ben duoi."

    if retrieval_notice:
        text = f"{retrieval_notice}\n{text}"

    sources = []
    for c in chunks:
        s = c.get("metadata", {}).get("source", "unknown")
        if s not in sources:
            sources.append(s)

    return {
        "answer": text,
        "chunks": chunks,
        "sources": sources,
    }


def main() -> None:
    print("=" * 60)
    print("Day08 RAG Chat Box")
    print("Type your question. Type 'exit' to quit.")
    print("=" * 60)

    while True:
        q = input("\nYou: ").strip()
        if not q:
            continue
        if q.lower() in {"exit", "quit", ":q"}:
            print("Bye.")
            break

        result = answer(q)
        print("\nAssistant:")
        print(result["answer"])

        print("\nUsed chunks:")
        for i, chunk in enumerate(result.get("chunks", []), 1):
            meta = chunk.get("metadata", {})
            source = meta.get("source", "unknown")
            section = meta.get("section", "")
            score = chunk.get("score", 0)
            preview = (chunk.get("text", "") or "")[:180].replace("\n", " ")

            header = f"  [{i}] {source}"
            if section:
                header += f" | {section}"
            header += f" | score={score:.2f}"

            print(header)
            print(f"      {preview}...")

        print("\nSources:")
        for i, s in enumerate(result["sources"], 1):
            print(f"  [{i}] {s}")


if __name__ == "__main__":
    main()

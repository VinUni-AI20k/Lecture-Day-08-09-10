# RAG Quick Start — Implementation Plan
## Stack: LangChain + Chroma + BM25S + OpenAI (gpt-4o-mini) + RAGAS

> **Mục tiêu:** Xây dựng prototype RAG hoàn chỉnh chạy được trên local,  
> đạt RAGAS score > 0.80 trên toàn bộ 10 test cases trong bộ `test_questions.json`.

---

## Mục lục

1. [Tổng quan & Dependencies](#1-tổng-quan--dependencies)
2. [Cấu trúc thư mục](#2-cấu-trúc-thư-mục-chuẩn-theo-scoringmd)
3. [Phase 1 — Xây dựng Index](#3-phase-1--xây-dựng-index-indexpy)
4. [Phase 2 — Retrieval & Generation](#4-phase-2--retrieval--generation-rag_answerpy)
5. [Phase 3 — Evaluation & Format log](#5-phase-3--evaluation--format-log-evalpy)
6. [Hướng dẫn chạy hệ thống](#6-hướng-dẫn-chạy-hệ-thống)
7. [Kết quả kỳ vọng](#7-kết-quả-kỳ-vọng)
8. [Troubleshooting](#10-troubleshooting)

---

## 1. Tổng quan & Dependencies

### Sơ đồ luồng dữ liệu

```
docs/*.txt
    │
    ▼
[1] Ingestion (parse metadata + semantic chunking)
    │
    ▼
[2] Indexing ──► Chroma (dense vector)
               ► BM25S  (sparse keyword)
    │
    ▼
[3] Retrieval  ◄── User query
    ├── Query rewriting (HyDE)
    ├── Hybrid search (dense + sparse)
    ├── RRF merging
    └── Reranking (CrossEncoder)
    │
    ▼
[4] Generation
    ├── Prompt builder (grounding rules)
    ├── gpt-4o-mini (temp=0)
    └── Answer + citation
    │
    ▼
[5] Evaluation (RAGAS metrics)
```

### Cài đặt dependencies

```bash
pip install langchain langchain-openai langchain-community
pip install chromadb
pip install bm25s
pip install sentence-transformers          # CrossEncoder reranking
pip install ragas datasets                 # evaluation
pip install python-dotenv tqdm rich        # utilities
```

**`requirements.txt`**

```
langchain==0.3.x
langchain-openai==0.2.x
langchain-community==0.3.x
chromadb==0.5.x
bm25s==0.2.x
sentence-transformers==3.x
ragas==0.2.x
datasets==3.x
openai==1.x
python-dotenv==1.x
tqdm==4.x
rich==13.x
```

### Biến môi trường

Tạo file `.env` ở root:

```env
OPENAI_API_KEY=sk-...your-key-here...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini
CHROMA_PERSIST_DIR=./data/chroma_db
BM25_INDEX_DIR=./data/bm25_index
DOCS_DIR=./data/docs
TOP_K_RETRIEVAL=10
TOP_K_RERANK=3
RELEVANCE_THRESHOLD=0.35
```

---

## 2. Cấu trúc thư mục chuẩn theo SCORING.md

```
rag_prototype/
│
├── .env                          # API keys & config
├── requirements.txt
│
├── data/                         # Thư mục dữ liệu
│   ├── docs/                     # Tài liệu nguồn (.txt)
│   ├── chroma_db/                # Chroma persistent storage (generated)
│   ├── bm25_index/               # BM25S serialized index (generated)
│   └── test_questions.json       # 10 test cases
│
├── logs/                         # File log chấm điểm
│   └── grading_run.json
│
├── results/                      # Output của scorecard
│   ├── scorecard_baseline.md
│   └── scorecard_variant.md
│
├── docs/                         # Tài liệu kỹ thuật
│   ├── architecture.md
│   └── tuning-log.md
│
├── reports/                      # Báo cáo cá nhân & nhóm
│   ├── group_report.md
│   └── individual/
│       └── [ten_thanh_vien].md
│
├── index.py                      # Phase 1: parse + chunk + index
├── rag_answer.py                 # Phase 2: retrieval + generation + CLI
└── eval.py                       # Phase 3: RAGAS eval + generate log
```

---

## 3. Phase 1 — Xây dựng Index (`index.py`)

**File:** `index.py`

Gộp quá trình Ingestion và Indexing vào cùng một file. Mục tiêu: đọc tài liệu từ `data/docs/`, parse metadata, semantic split, và tạo cả 2 index (Chroma + BM25S).

```python
# index.py
import os
import re
import pickle
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

import bm25s
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

# --- CẤU HÌNH ---
DOCS_DIR = os.getenv("DOCS_DIR", "./data/docs")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
BM25_INDEX_DIR = os.getenv("BM25_INDEX_DIR", "./data/bm25_index")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

ALIAS_MAP = {
    "it/access-control-sop.md": [
        "approval matrix for system access",
        "approval matrix",
        "access control sop",
    ]
}

# --- BƯỚC 1: INGESTION ---
def parse_header_metadata(content: str) -> Dict[str, Any]:
    metadata = {}
    header_pattern = re.compile(r"^(Source|Department|Effective Date|Access):\s*(.+)$", re.MULTILINE)
    for match in header_pattern.finditer(content):
        metadata[match.group(1).lower().replace(" ", "_")] = match.group(2).strip()
    return metadata

def split_by_sections(content: str) -> List[Dict[str, str]]:
    pattern = re.compile(r"={3,}\s*(.+?)\s*={3,}", re.MULTILINE)
    sections = []
    matches = list(pattern.finditer(content))
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end].strip()
        if body: sections.append({"title": title, "body": body})
    if not sections: sections.append({"title": "Full Document", "body": content.strip()})
    return sections

def load_documents(docs_dir: str) -> List[Document]:
    all_documents = []
    txt_files = list(Path(docs_dir).glob("*.txt"))
    for filepath in txt_files:
        content = filepath.read_text(encoding="utf-8")
        meta = parse_header_metadata(content)
        source = meta.get("source", filepath.stem)
        aliases = ALIAS_MAP.get(source, [])
        sections = split_by_sections(content)
        
        for sec_idx, section in enumerate(sections):
            chunk_text = f"[{section['title']}]\n{section['body']}"
            if aliases and sec_idx == 0:
                chunk_text += f"\n[Tên khác: {', '.join(aliases)}]"
                
            doc = Document(
                page_content=chunk_text,
                metadata={
                    "source": source,
                    "department": meta.get("department", "unknown"),
                    "effective_date": meta.get("effective_date", ""),
                    "section": section["title"],
                    "filename": filepath.name,
                    "aliases": aliases,
                    "chunk_id": f"{filepath.stem}_sec{sec_idx}",
                }
            )
            all_documents.append(doc)
    return all_documents

# --- BƯỚC 2: INDEXING ---
def build_indexes(documents: List[Document]):
    # 1. Chroma Index
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    print(f"[Chroma] Đang build index từ {len(documents)} chunks...")
    Chroma.from_documents(documents=documents, embedding=embeddings, persist_directory=CHROMA_PERSIST_DIR)

    # 2. BM25S Index
    Path(BM25_INDEX_DIR).mkdir(parents=True, exist_ok=True)
    print(f"[BM25S] Đang build index từ {len(documents)} chunks...")
    corpus = [doc.page_content for doc in documents]
    corpus_tokens = bm25s.tokenize(corpus, stopwords=None)
    retriever = bm25s.BM25()
    retriever.index(corpus_tokens)
    
    with open(f"{BM25_INDEX_DIR}/bm25.pkl", "wb") as f: pickle.dump(retriever, f)
    with open(f"{BM25_INDEX_DIR}/docs.pkl", "wb") as f: pickle.dump(documents, f)

if __name__ == "__main__":
    docs = load_documents(DOCS_DIR)
    build_indexes(docs)
    print("✅ Đã tạo Index thành công.")
```

---

## 4. Phase 2 — Retrieval & Generation (`rag_answer.py`)

**File:** `rag_answer.py`

Gộp pipeline retrieval (Hybrid search + rerank) và generation (gpt-4o-mini). Đầu ra kết hợp CLI.

```python
# rag_answer.py
import os
import sys
import pickle
import bm25s
from typing import List, Tuple, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.schema.messages import SystemMessage, HumanMessage
from sentence_transformers import CrossEncoder

load_dotenv()

# --- CẤU HÌNH ---
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
BM25_INDEX_DIR = os.getenv("BM25_INDEX_DIR", "./data/bm25_index")
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", 10))
TOP_K_RERANK = int(os.getenv("TOP_K_RERANK", 3))
THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", 0.35))

# --- LOAD INDEXES ---
_chroma, _bm25_retriever, _bm25_docs = None, None, None

def load_indexes():
    global _chroma, _bm25_retriever, _bm25_docs
    if _chroma is None:
        embeddings = OpenAIEmbeddings(model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
        _chroma = Chroma(persist_directory=CHROMA_PERSIST_DIR, embedding_function=embeddings)
        with open(f"{BM25_INDEX_DIR}/bm25.pkl", "rb") as f: _bm25_retriever = pickle.load(f)
        with open(f"{BM25_INDEX_DIR}/docs.pkl", "rb") as f: _bm25_docs = pickle.load(f)
    return _chroma, _bm25_retriever, _bm25_docs

# --- RETRIEVAL PIPELINE ---
def rewrite_query_hyde(query: str, llm: ChatOpenAI) -> str:
    prompt = f"Trả lời câu hỏi sau bằng 100 từ giả định:\nCâu hỏi: {query}\nTrả lời:"
    try: return f"{query}\n\n{llm.invoke(prompt).content.strip()}"
    except: return query

def hybrid_search(query: str, top_k=TOP_K_RETRIEVAL) -> List[Tuple[Document, float]]:
    chroma, bm25, bm25_docs = load_indexes()
    
    # Dense
    dense_results = chroma.similarity_search_with_score(query, k=top_k)
    
    # Sparse
    q_tokens = bm25s.tokenize([query], stopwords=None)
    results, scores = bm25.retrieve(q_tokens, corpus=bm25_docs, k=top_k)
    sparse_results = list(zip(results[0], scores[0])) if len(scores) > 0 else []
    
    # RRF 
    score_map = {}
    for rank, (doc, _) in enumerate(dense_results):
        cid = doc.metadata.get("chunk_id", doc.page_content[:50])
        score_map[cid] = (doc, score_map.get(cid, (doc, 0.0))[1] + 1.0/(60+rank))
    for rank, (doc, _) in enumerate(sparse_results):
        cid = doc.metadata.get("chunk_id", doc.page_content[:50])
        score_map[cid] = (doc, score_map.get(cid, (doc, 0.0))[1] + 1.0/(60+rank))
        
    merged = sorted(score_map.values(), key=lambda x: x[1], reverse=True)
    return merged[:top_k]

_reranker = None
def rerank(query: str, candidates: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
    global _reranker
    if _reranker is None: _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    docs = [doc for doc, _ in candidates]
    pairs = [(query, doc.page_content[:512]) for doc in docs]
    scores = _reranker.predict(pairs)
    return sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)[:TOP_K_RERANK]

# --- GENERATION ---
SYSTEM_PROMPT = "Bạn là trợ lý hỗ trợ nội bộ. CHỈ được trả lời dựa trên CONTEXT. Nếu context không có, hãy trả lời: 'Không tìm thấy thông tin.' Luôn cite [Nguồn: ...]"

def generate_answer(query: str, reranked_docs: List[Tuple[Document, float]], llm) -> Dict[str, Any]:
    if not reranked_docs or reranked_docs[0][1] < THRESHOLD:
        return {"answer": "Không tìm thấy thông tin trong tài liệu hiện có.", "sources": [], "chunks_used": [], "has_context": False}

    context_parts = []
    sources = set()
    for idx, (doc, _) in enumerate(reranked_docs, 1):
        src = doc.metadata.get("source", "unknown")
        sources.add(src)
        context_parts.append(f"--- Context [{idx}] | Nguồn: {src} ---\n{doc.page_content}")
    
    human_msg = "\n".join(context_parts) + f"\n\nCâu hỏi: {query}"
    
    answer = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=human_msg)]).content.strip()
    
    return {
        "answer": answer,
        "sources": list(sources),
        "chunks_used": [doc.page_content for doc, _ in reranked_docs],
        "has_context": True,
        "config": {"retrieval_mode": "hybrid"}
    }

def rag_answer(query: str, retrieval_mode="hybrid", verbose=False) -> Dict[str, Any]:
    llm = ChatOpenAI(model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"), temperature=0)
    search_query = rewrite_query_hyde(query, llm) if retrieval_mode == "hybrid" else query
    
    if retrieval_mode == "hybrid":
        candidates = hybrid_search(search_query)
    else:
        chroma, _, _ = load_indexes()
        candidates = chroma.similarity_search_with_score(search_query, k=TOP_K_RETRIEVAL)
        
    reranked = rerank(query, candidates)
    res = generate_answer(query, reranked, llm)
    res["config"]["retrieval_mode"] = retrieval_mode
    
    if verbose:
        print(f"Q: {query}\nA: {res['answer']}\nSources: {res['sources']}")
    return res

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "SLA của ticket P1?"
    rag_answer(q, verbose=True)
```

---

## 5. Phase 3 — Evaluation & Format log (`eval.py`)

**File:** `eval.py`

File này thưc thi quá trình run tập test `data/test_questions.json`, tính điểm RAGAS và chuẩn bị format xuất log vào `logs/` theo đúng schema nộp bài.

```python
# eval.py
import json
import os
import sys
from datetime import datetime
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from rag_answer import rag_answer

def run_eval(questions_path: str, mode: str = "hybrid") -> list[dict]:
    with open(questions_path, encoding="utf-8") as f:
        questions = json.load(f)

    results = []
    for q in questions:
        print(f"Running {q['id']}: {q['question'][:50]}...")
        result = rag_answer(q["question"], retrieval_mode=mode, verbose=False)
        results.append({
            "id": q["id"],
            "question": q["question"],
            "answer": result["answer"],
            "sources": result["sources"],
            "contexts": result["chunks_used"],
            "expected_answer": q.get("expected_answer", ""),
            "expected_sources": q.get("expected_sources", []),
            "has_context": result["has_context"],
            "retrieval_mode": mode
        })
    return results

def compute_ragas_scores(results: list[dict]) -> dict:
    dataset = Dataset.from_dict({
        "question":     [r["question"] for r in results],
        "answer":       [r["answer"] for r in results],
        "contexts":     [r.get("contexts", []) for r in results],
        "ground_truth": [r["expected_answer"] for r in results],
    })
    
    llm = LangchainLLMWrapper(ChatOpenAI(model=os.getenv("OPENAI_CHAT_MODEL")))
    emb = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model=os.getenv("OPENAI_EMBEDDING_MODEL")))
    
    scores = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_precision, context_recall], llm=llm, embeddings=emb)
    return scores

def save_grading_log(results: list[dict], output_path: str = "logs/grading_run.json"):
    os.makedirs("logs", exist_ok=True)
    log = []
    for r in results:
        log.append({
            "id": r["id"],
            "question": r["question"],
            "answer": r["answer"],
            "sources": r["sources"],
            "chunks_retrieved": len(r.get("contexts", [])),
            "retrieval_mode": r["retrieval_mode"],
            "timestamp": datetime.now().isoformat(),
        })
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"Grading log saved to {output_path}")

if __name__ == "__main__":
    mode = "hybrid"
    
    if "--input" in sys.argv:
        idx = sys.argv.index("--input")
        input_path = sys.argv[idx+1]
        print(f"Chạy tập questions từ {input_path}")
        results = run_eval(input_path, mode=mode)
        save_grading_log(results)
    else:
        results = run_eval("data/test_questions.json", mode=mode)
        scores = compute_ragas_scores(results)
        print("RAGAS Scores:", scores)
```

---

## 6. Hướng dẫn chạy hệ thống

### Bước 1: Build Index
Tải các `.txt` từ `data/docs/` lên Chroma và BM25S.
```bash
python index.py
```

### Bước 2: Truy vấn Test CLI
Trả lời từng câu một trực tiếp.
```bash
python rag_answer.py "SLA xử lý ticket P1 là bao lâu?"
```

### Bước 3: Chạy RAGAS Validation
Đánh giá chất lượng của toàn bộ 10 questions test nội bộ.
```bash
python eval.py
```

### Bước 4: Chạy Grading lấy log giao nộp (Lúc 17:00)
Chạy script sinh log cho `grading_questions.json`. Log `logs/grading_run.json` sẽ được sinh ra đúng cấu trúc được đưa ra ở SCORING.md.
```bash
python eval.py --input grading_questions.json
```

---

## 7. Kết quả kỳ vọng

### RAGAS Scores (target)

| Metric | Target | Ghi chú |
|---|---|---|
| Faithfulness | > 0.90 | gpt-4o-mini + temp=0 giúp grounding chặt |
| Answer Relevancy | > 0.85 | HyDE + hybrid search tăng recall |
| Context Precision | > 0.80 | Reranking lọc bỏ noise |
| Context Recall | > 0.80 | BM25S bắt được q07 alias |
| **Abstain Accuracy** | **= 1.00** | Threshold check bắt q09 |

### Mapping test cases quan trọng

| Q | Vấn đề | Giải pháp trong pipeline |
|---|---|---|
| q07 | Query dùng tên cũ "Approval Matrix" | BM25S bắt alias + alias được ghi vào chunk |
| q09 | ERR-403-AUTH không có trong docs | Threshold < 0.35 → abstain, không hallucinate |
| q10 | VIP refund — policy không đề cập | LLM chỉ trả về policy chuẩn + ghi chú không có quy trình riêng |

---

## 10. Troubleshooting

### ChromaDB conflict khi rebuild

```bash
rm -rf ./data/chroma_db ./data/bm25_index
python pipeline.py   # rebuild từ đầu
```

### CrossEncoder lần đầu chạy chậm

Model `ms-marco-MiniLM-L-6-v2` (~90MB) sẽ tự download lần đầu tiên. Chạy một lần trước để cache:

```python
from sentence_transformers import CrossEncoder
CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
```

### Abstain score thấp (q09 bị trả lời sai)

Hạ threshold trong `.env`:

```env
RELEVANCE_THRESHOLD=0.40   # tăng lên để abstain nhiều hơn
```

Nếu vẫn fail, kiểm tra CrossEncoder có đang chạy đúng không — score của q09 phải < threshold.

### RAGAS trả về NaN

Thường do context rỗng cho một số câu hỏi. Đảm bảo `contexts` luôn là `List[str]` (list rỗng `[]` thay vì `None`).

### Rate limit OpenAI

Thêm retry logic hoặc dùng `langchain.globals.set_llm_cache()` để cache API calls trong quá trình dev.

---

## Chi phí ước tính (OpenAI API)

| Bước | Token ước tính / query | Chi phí (gpt-4o-mini) |
|---|---|---|
| HyDE rewriting | ~200 tokens | ~$0.00006 |
| Generation | ~800 tokens | ~$0.00024 |
| RAGAS eval (10 queries) | ~50,000 tokens | ~$0.015 |
| Embedding (1 lần index) | ~15,000 tokens | ~$0.0015 |
| **Tổng prototype** | | **< $0.05** |

---

*Plan version 1.0 — April 2026*  
*Stack: LangChain + Chroma + BM25S + OpenAI gpt-4o-mini + RAGAS*`
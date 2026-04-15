# SPRINT 2: RAG Baseline - Quick Start Guide

## N.Hoàng (P2: RAG Developer)

---

## 📋 Tóm tắt những gì đã làm (Sprint 2)

Hoàn thành implementation Baseline RAG Pipeline:

✅ **`retrieve_dense()`** - Dense retrieval từ ChromaDB

- Query embedding giống như khi index
- Trả về Top-K chunks với similarity scores
- Xử lý metadata đầy đủ (source, section, effective_date)

✅ **`call_llm()`** - LLM integration (OpenAI + Gemini)

- Auto-detect API key
- Temperature=0 cho output ổn định
- Proper error handling

✅ **`rag_answer()`** - RAG Pipeline hoàn chỉnh

- Retrieve → Build Context → Generate → Extract Sources
- Hỗ trợ verbose mode để debug

✅ **Citation & Abstain**

- Format: `[1] source | section | score=0.85`
- Prompt ép model trích dẫn [1], [2], [3]
- Nếu insufficient context → model sẽ nói "không đủ dữ liệu"

---

## 🚀 Cách chạy Baseline

### Step 1: Chuẩn bị (First Time)

```bash
# 1. Cài dependencies
pip install -r requirements.txt

# 2. Cấu hình .env (điền API key thực)
# Chọn một trong hai:
# A) OpenAI: OPENAI_API_KEY=sk-...
# B) Gemini: GOOGLE_API_KEY=...

# 3. Build index từ Sprint 1 (nếu chưa có)
python index.py

# Kiểm tra: phải có file chroma_db/ sau lệnh này
```

### Step 2: Chạy Baseline

```bash
# Chạy test 4 queries mẫu từ test_questions.json
python rag_answer.py

# Output sẽ hiển thị:
# - Query
# - Retrieved chunks (3 top chunks)
# - Answer từ LLM (có [1], [2], [3] citations)
# - Sources
```

### Step 3: Test một query cụ thể

```python
from rag_answer import rag_answer

# Ví dụ 1: Query có answer trong docs
result = rag_answer(
    query="SLA xử lý ticket P1 là bao lâu?",
    verbose=True
)
print("Answer:", result["answer"])
print("Sources:", result["sources"])

# Ví dụ 2: Query không có trong docs (kiểm tra abstain)
result = rag_answer(
    query="ERR-403-AUTH là lỗi gì?",
    verbose=True
)
print("Answer:", result["answer"])  # Sẽ có "không đủ dữ liệu"
```

---

## ✅ Verification Checklist (Definition of Done Sprint 2)

Chạy các test này để confirm Baseline chạy đúng:

- [ ] `python rag_answer.py` chạy không crash
- [ ] Query 1: "SLA xử lý ticket P1 là bao lâu?"
  - Answer phải có citation `[1]` → source là `sla_p1_2026.txt`
- [ ] Query 3: "Ai phải phê duyệt để cấp quyền Level 3?"
  - Answer phải có citation từ `access_control_sop.txt`
- [ ] Query 4: "ERR-403-AUTH là lỗi gì?"
  - Answer phải là "không đủ dữ liệu" (abstain) vì không trong docs
- [ ] Similarity scores > 0.5 để chunks được chọn
- [ ] Context block format đúng: `[1] source | section | score=X.XX`

---

## 💡 Troubleshooting

### Lỗi 1: "chromadb.PersistentClient - collection not found"

```
❌ ChromaDB collection not found
✅ Fix: Chạy `python index.py` trước
```

### Lỗi 2: "OPENAI_API_KEY chưa được cấu hình"

```
❌ ValueError: Không tìm thấy API key
✅ Fix: Điền OPENAI_API_KEY hoặc GOOGLE_API_KEY vào .env
```

### Lỗi 3: "Embedding model không khớp"

```
❌ Vector dimensions mismatch
✅ Fix: Dùng cùng EMBEDDING_PROVIDER ở index.py và rag_answer.py
        (cả hai phải là "openai" hoặc "local")
```

### Lỗi 4: "call_llm() returns empty string"

```
❌ Answer trống
✅ Fix: Check API key valid, temperature=0, max_tokens=512
```

---

## 📊 Output Format (Spring 2 → Eval, Sprint 3)

Mỗi `rag_answer()` trả về:

```python
{
    "query": "SLA xử lý ticket P1 là bao lâu?",
    "answer": "Ticket P1 có SLA phản hồi ban đầu 15 phút và thời gian xử lý (resolution) là 4 giờ. [1]",
    "sources": ["sla_p1_2026.txt"],
    "chunks_used": [
        {
            "text": "P1 tickets - Response SLA: 15 minutes...",
            "metadata": {"source": "sla_p1_2026.txt", "section": "Priority Levels", "score": 0.87},
            "score": 0.87
        },
        ...
    ],
    "config": {
        "retrieval_mode": "dense",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": False
    }
}
```

---

## 🎯 Công việc tiếp theo (Sprint 3 - Tuning)

Sau khi Baseline chạy ổn định:

1. **Implement 1 Variant** (chọn 1):
   - [ ] Hybrid: Dense + BM25 (keyword search)
   - [ ] Rerank: Cross-encoder để chấm lại relevance
   - [ ] Query Transform: Expansion, decomposition, HyDE

2. **Compare A/B**: Chạy cùng 10 queries trên cả Baseline và Variant

3. **Document**: Ghi lý do chọn variant vào `docs/tuning-log.md`

4. **Evaluate**: Sprint 4 sẽ chạy `eval.py` để tính scorecard

---

## 📝 Next Communication with Nhóm

**Báo cáo cho Data Engineer (P1 - Vì dữ liệu)**:

- ✅ Metadata format chúng ta statng đã tốt (source, section, effective_date)
- ✅ ChromaDB query chạy mượt

**Báo cáo cho Document Team (P5 - Vinh)**:

- Baseline RAG pipeline sẵn sàng để document architecture
- Có thể start vẽ sơ đồ luồng dữ liệu

**Chuẩn bị cho Optimization (P3 - Việt)**:

- Baseline benchmark scores sẽ có sau Sprint 4 eval
- Sẽ test Hybrid hoặc Rerank variants

---

## 📞 Reference Documentation

- **RAG Paper**: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
- **Prompt Engineering**: https://platform.openai.com/docs/guides/prompt-engineering
- **ChromaDB Guide**: https://docs.trychroma.com/
- **Citation in RAG**: Use [1], [2], ... để dễ extract và verify sources

---

**Status**: ✅ Sprint 2 Baseline HOÀN THÀNH 🎉
**Ready for**: Sprint 3 Tuning + Sprint 4 Evaluation

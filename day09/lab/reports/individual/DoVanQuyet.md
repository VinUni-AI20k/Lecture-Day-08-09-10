# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Đỗ Văn Quyết
**Vai trò trong nhóm:** Worker Owner
**Ngày nộp:** 14/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi chịu trách nhiệm hai file worker chính và MCP server trong hệ thống multi-agent. Cụ thể:

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/retrieval.py`, `workers/policy_tool.py`, `mcp_server.py`
- Functions tôi implement:
  - `retrieval.py`: `_get_embedding_fn()`, `retrieve_dense()`, `run()`
  - `policy_tool.py`: `_analyze_with_llm()`, `run()`
  - `mcp_server.py`: `tool_search_kb()`, `tool_get_ticket_info()`, `tool_check_access_permission()`, `tool_create_ticket()`, `_load_tickets()`, `_save_tickets()`

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Supervisor Owner (graph.py) route câu hỏi đến worker nào là do logic trong `supervisor_node`. Worker của tôi nhận `state` từ supervisor, xử lý, rồi trả state đã cập nhật để `synthesis_worker` tổng hợp câu trả lời cuối. Nếu worker chưa xong, toàn bộ pipeline bị block.

**Bằng chứng:**
`workers/retrieval.py` — function `run()` nhận `AgentState` và append vào `workers_called`:
```python
state["workers_called"].append("retrieval_worker")
```
Trace `gq01` xác nhận: `"workers_called": ["retrieval_worker"]`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Dùng **OpenAI `text-embedding-3-small`** (1536 chiều) làm embedding function trong `retrieval.py` thay vì SentenceTransformers (384 chiều).

Ban đầu file `retrieval.py` có fallback sang `SentenceTransformers` nếu không có API key. Tôi đã xoá fallback này và chỉ dùng OpenAI embeddings.

**Lý do:** ChromaDB index được build bằng `index.py` dùng OpenAI `text-embedding-3-small` (vector 1536 chiều). Nếu retrieval dùng SentenceTransformers (384 chiều), dimension mismatch sẽ xảy ra và ChromaDB trả về lỗi hoặc kết quả ngẫu nhiên. Phải giữ nhất quán embedding model giữa lúc index và lúc query.

**Các lựa chọn thay thế:**
- Rebuild index bằng SentenceTransformers → tốn thêm thời gian build lại 29 chunks
- Dùng hai collection riêng → phức tạp không cần thiết
- Chỉ dùng OpenAI → đơn giản, nhất quán ✓

**Trade-off đã chấp nhận:** Retrieval phụ thuộc hoàn toàn vào API key OpenAI. Nếu mất kết nối thì không fallback được. Trong lab điều này chấp nhận được.

**Bằng chứng từ code:**
```python
# workers/retrieval.py
def _get_embedding_fn():
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    def embed(texts):
        resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
        return [d.embedding for d in resp.data]
    return embed
```
Trace `gq01`: `"sources": ["escalation.txt", "ticket_priority.txt", "sla_p1.txt"]` — retrieval trả về đúng chunks liên quan đến SLA P1.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `retrieval.py` dùng path ChromaDB tương đối (`./chroma_db`) lấy từ biến môi trường.

**Symptom:** Khi chạy `mcp_server.py` hoặc `eval_trace.py` từ thư mục khác (không phải `lab/`), tool `search_kb` trả về `results: []` — không tìm thấy document nào dù index đã được build.

**Root cause:**
```python
# Trước khi sửa — bị lỗi khi chạy từ thư mục khác
chroma_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")
```
`./chroma_db` là path tương đối so với **current working directory**, không phải so với file. Khi chạy từ `day09/` thì path resolve thành `day09/chroma_db` — không tồn tại.

**Cách sửa:** Dùng `Path(__file__)` để tính absolute path so với vị trí file:
```python
# Sau khi sửa — hoạt động từ bất kỳ thư mục nào
from pathlib import Path
chroma_path = str(Path(__file__).parent.parent / "chroma_db")
```

**Bằng chứng trước/sau:**

*Trước:*
```
Test: search_kb
  (no results)
```

*Sau:*
```
Test: search_kb
  [0.4551] support/sla-p1-2026.pdf: v2026.1 (2026-01-15)...
  [0.3893] support/sla-p1-2026.pdf: Ticket P1: Phản hồi ban đầu 15 phút...
```

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi debug và fix lỗi ChromaDB path nhanh bằng cách trace ngược từ symptom (empty results) → root cause (relative path) → fix bằng `Path(__file__)`. Đây là loại lỗi dễ bỏ sót vì chỉ xảy ra khi chạy từ thư mục khác.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
`policy_tool.py` của tôi xử lý logic rule-based tốt nhưng phần phân tích LLM còn đơn giản — chỉ detect keyword mà chưa hiểu ngữ cảnh phức tạp (VD: kết hợp nhiều điều kiện exception cùng lúc).

**Nhóm phụ thuộc vào tôi ở đâu?**
Toàn bộ pipeline phụ thuộc vào `workers/` — nếu `retrieval.py` không trả chunks đúng thì không có evidence để tổng hợp, answer sẽ rỗng hoặc sai.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi cần `graph.py` (Supervisor Owner) định nghĩa đúng `AgentState` schema và gọi đúng interface `run(state) -> state` của các worker.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ cải thiện `retrieval.py` để hỗ trợ **hybrid search** — kết hợp dense embedding (hiện tại) với BM25 sparse search. Với các câu hỏi chứa từ khóa kỹ thuật cụ thể (mã ticket, tên SLA như "P1", "P2"), BM25 cho recall tốt hơn pure embedding. Hybrid search sẽ tăng độ chính xác cho `gq05`, `gq08` — các câu hỏi về ticket priority và SLA deadline cụ thể mà hiện tại retrieval chỉ trả về chunk gần đúng.

---

*Lưu file này với tên: `reports/individual/worker_owner.md`*

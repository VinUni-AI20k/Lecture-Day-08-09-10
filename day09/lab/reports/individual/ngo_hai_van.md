# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Ngô Hải Văn  
**Vai trò trong nhóm:** MCP Owner — Sprint 3  
**Ngày nộp:** 2026-04-14  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào?

**Module/file tôi chịu trách nhiệm:**
- File chính: `mcp_server.py`
- Files sửa: `workers/policy_tool.py`, `workers/retrieval.py`, `graph.py`
- Functions tôi implement/fix:
  - `mcp_server.py`: `tool_search_kb()`, `tool_get_ticket_info()`, `tool_check_access_permission()`, `tool_create_ticket()`, `dispatch_tool()`, `list_tools()`
  - `workers/policy_tool.py`: sửa hàm `run()` — logic khi nào gọi MCP
  - `workers/retrieval.py`: sửa `_get_embedding_fn()` và `_get_collection()` — thêm sentence-transformers fallback
  - `graph.py`: cập nhật `route_decision()` — thêm MCP enabled/disabled vào `route_reason`

**Cách công việc của tôi kết nối với phần của thành viên khác:**  
`mcp_server.py` là external capability layer — `policy_tool_worker` (Sprint 2 của Dũng) gọi vào qua `_call_mcp_tool()`. Supervisor (Sprint 1 của Vương) set `needs_tool=True` để báo hiệu cho policy_tool biết cần dùng MCP. Tôi không sửa logic core của Sprint 1 hay Sprint 2, chỉ implement interface và fix điểm tích hợp.

**Bằng chứng:** Commit `845c303` — `sprint3(Van): implement MCP integration with sentence-transformers fallback`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Dùng `sentence-transformers` thay `OpenAI embeddings` cho ChromaDB, và sửa điều kiện trigger MCP từ `if not chunks and needs_tool` thành `if needs_tool`.

**Bối cảnh:** Khi nhận code từ Sprint 2, ChromaDB index được build bằng `OpenAIEmbeddingFunction` (trong `build_index.py`). `mcp_server.py`'s `search_kb` gọi `retrieve_dense()` từ `retrieval.py`, nhưng `retrieval.py` không pass đúng embedding function → ChromaDB báo lỗi `CHROMA_OPENAI_API_KEY not set`. Không thể dùng OpenAI vì không có API key.

**Các lựa chọn thay thế:**
1. Yêu cầu team set `OPENAI_API_KEY` — không khả thi vì không phải ai cũng có key
2. Dùng `query_texts=["..."]` trực tiếp với collection cũ — vẫn cần embedding function khớp với index
3. Rebuild index bằng `sentence-transformers` + sửa `_get_collection()` — offline, không cần API key

**Lý do chọn option 3:** `sentence-transformers/all-MiniLM-L6-v2` đã được cài sẵn trong môi trường. Embedding phải nhất quán giữa lúc index và lúc query — rebuild index với ST đảm bảo điều đó. Không phụ thuộc API key của bất kỳ thành viên nào.

**Trade-off đã chấp nhận:** Embedding quality của ST thấp hơn `text-embedding-3-small` (OpenAI), nhưng đủ để retrieve đúng document cho 5 tài liệu nhỏ trong lab.

**Bằng chứng từ trace — trước và sau fix:**

```
# Trước fix (search_kb):
"chunks": [], "sources": [], "total_found": 0
⚠️  ChromaDB query failed: The CHROMA_OPENAI_API_KEY environment variable is not set.

# Sau fix (search_kb trong trace run_20260414_155335.json):
"mcp_tools_used": [
  {
    "tool": "search_kb",
    "input": {"query": "Khách hàng Flash Sale yêu cầu hoàn tiền...", "top_k": 3},
    "output": {"chunks": [...], "sources": ["policy_refund_v4.txt"], "total_found": 3}
  }
]
```

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** `mcp_tools_used` luôn là `[]` trong trace dù route là `policy_tool_worker` và `needs_tool=True`.

**Symptom:** Chạy pipeline với câu "Khách hàng Flash Sale yêu cầu hoàn tiền", trace cho thấy `supervisor_route: policy_tool_worker`, `needs_tool: true`, nhưng `mcp_tools_used: []`. MCP không được gọi dù đã implement đúng trong `policy_tool.py`.

**Root cause:** `policy_tool_worker_node` trong `graph.py` (Sprint 1) gọi `retrieval_run(state)` trước khi gọi `policy_tool_run(state)` để đảm bảo có evidence:

```python
def policy_tool_worker_node(state):
    if not state.get("retrieved_chunks"):
        state = retrieval_run(state)   # ← fill chunks trước
    return policy_tool_run(state)
```

Khi `policy_tool.py`'s `run()` chạy, `retrieved_chunks` đã có sẵn → điều kiện `if not chunks and needs_tool` không bao giờ đúng → MCP `search_kb` không được trigger.

**Cách sửa:** Đổi điều kiện trigger MCP trong `workers/policy_tool.py`:

```python
# Trước:
if not chunks and needs_tool:
    mcp_result = _call_mcp_tool("search_kb", ...)

# Sau:
if needs_tool:   # luôn gọi MCP khi supervisor quyết định cần tool
    mcp_result = _call_mcp_tool("search_kb", ...)
```

**Bằng chứng trước/sau:**

```
# Trước (trace cũ — Sprint 2):
"workers_called": ["retrieval_worker", "policy_tool_worker", "synthesis_worker"]
"mcp_tools_used": []

# Sau (trace run_20260414_155343.json — Sprint 3):
"workers_called": ["retrieval_worker", "policy_tool_worker", "synthesis_worker"]
"mcp_tools_used": ["search_kb", "check_access_permission", "get_ticket_info"]
```

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào:**  
Debug trace-driven — khi `mcp_tools_used: []`, thay vì đoán mò tôi đọc trace JSON và `workers_called` để xác định chính xác thứ tự gọi, rồi trace ngược lên `graph.py` để tìm root cause. Cách tiếp cận này nhanh hơn đọc code từ đầu và cho ra fix chính xác ngay lần đầu.

**Tôi làm chưa tốt:**  
Không kiểm tra embedding consistency sớm. Lẽ ra khi nhận `build_index.py` từ Sprint 2, tôi phải chạy `python3 mcp_server.py` ngay để verify `search_kb` hoạt động trước khi implement các tool khác. Phát hiện lỗi embedding muộn làm mất thêm thời gian rebuild index.

**Nhóm phụ thuộc vào tôi ở đâu:**  
Nếu Sprint 3 chưa xong, `policy_tool_worker` không gọi được MCP → trace không có `mcp_tools_used` → mất 5 điểm Sprint 3 DoD. Toàn bộ câu hỏi access control (gq03, gq09) không có `check_access_permission` tool → kết quả thiếu context.

**Tôi phụ thuộc vào thành viên khác:**  
Cần Sprint 1 (Vương) set `needs_tool=True` đúng trong `route_decision()` mới có tín hiệu để trigger MCP. Cần Sprint 2 (Sang) có `_get_collection()` đúng để `retrieve_dense()` hoạt động và `search_kb` có data để query.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ implement **MCP HTTP server thật** dùng `FastAPI` thay mock class trong Python. Lý do: trace `run_20260414_155343.json` cho thấy câu gq09 (Level 3 + P1) gọi 3 MCP tools trong 1 request — nếu là HTTP server thật, 3 calls này có thể song song thay vì tuần tự, giảm latency từ ~8s xuống ~4s. Bonus +2 điểm theo SCORING.md và là kiến trúc chuẩn MCP spec hơn.

---

*File lưu tại: `reports/individual/ngo_hai_van.md`*  
*Commit sau 18:00 được phép theo SCORING.md*

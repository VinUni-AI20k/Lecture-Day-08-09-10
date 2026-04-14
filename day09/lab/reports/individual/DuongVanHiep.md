# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Dương Văn Hiệp  
**Vai trò trong nhóm:** Worker Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi phụ trách lớp worker của pipeline multi-agent: `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py`, và cập nhật contract trong `contracts/worker_contracts.yaml`. Ở `retrieval.py`, tôi implement `retrieve_dense()`, `_extract_relevant_sentences()`, và `run()` để worker lấy evidence từ ChromaDB hoặc fallback lexical search rồi rút gọn thành các câu liên quan nhất. Ở `policy_tool.py`, tôi làm `_call_mcp_tool()`, `analyze_policy()`, và `run()` để xử lý exception như Flash Sale, digital product, activated product, đồng thời gọi MCP tools khi supervisor bật `needs_tool=True`. Ở `synthesis.py`, tôi làm `_build_context()`, `_fallback_grounded_answer()`, `_estimate_confidence()`, `synthesize()`, và `run()` để sinh câu trả lời grounded, có citation và confidence. Phần của tôi nối trực tiếp với supervisor vì supervisor chỉ route; chất lượng answer thực tế phụ thuộc vào output đúng contract của worker.

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py`, `contracts/worker_contracts.yaml`
- Functions tôi implement: `retrieve_dense()`, `_extract_relevant_sentences()`, `_call_mcp_tool()`, `analyze_policy()`, `_build_context()`, `_fallback_grounded_answer()`, `synthesize()`, `run()`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Supervisor Owner quyết định `supervisor_route`, còn tôi đảm bảo worker nhận state đó và trả về đúng các field downstream cần dùng như `retrieved_chunks`, `policy_result`, `mcp_result`, `final_answer`, `confidence`. MCP Owner cung cấp server/tool schema; tôi chịu trách nhiệm phần client-side integration trong worker. Trace & Docs Owner dùng chính `worker_io_logs`, `mcp_tool_called`, và `mcp_result` mà tôi ghi vào state để viết báo cáo và debug trace.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

| Claim | Evidence |
|---|---|
| Tôi làm worker layer | `git log -- workers/*.py contracts/worker_contracts.yaml` ra các commit `3c57326`, `9b972c9`, `3e24c6d` |
| Tôi cập nhật contract | `worker_contracts.yaml`: `status: "TODO Sprint 2"` -> `status: "done"` |
| Worker có output thật trong trace | `run_20260414_175752_203869.json`: `worker_io_logs[0].worker = "policy_tool_worker"` và `worker_io_logs[1].worker = "synthesis_worker"` |

```yaml
actual_implementation:
  status: "done"
  notes: "Returns grounded final_answer with citations..."
```

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi chọn để `policy_tool_worker` tự backfill evidence qua MCP khi `needs_tool=True`, thay vì bắt buộc mọi câu policy phải đi qua `retrieval_worker` trước.

**Lý do:**

Tôi muốn policy worker đủ “độc lập” để xử lý trọn một câu hỏi nghiệp vụ có tool support. Nếu ép flow `supervisor -> retrieval_worker -> policy_tool_worker -> synthesis_worker`, pipeline sẽ coupling hơn và khó mở rộng khi policy worker cần thêm các tool đặc thù như `check_access_permission` hay `get_ticket_info`. Trong bản hiện tại, khi `chunks` rỗng nhưng `needs_tool=True`, worker tự gọi `search_kb`, sau đó phân tích policy, và nếu là access question thì gọi tiếp `check_access_permission` và `get_ticket_info`. Cách này giúp `gq09` chạy trọn nhánh tool-assisted chỉ với `policy_tool_worker -> synthesis_worker`.

**Trade-off đã chấp nhận:**

Trade-off là policy worker trở nên “nặng” hơn và dễ kéo thêm noise từ nhiều nguồn cùng lúc. Trace `run_20260414_175752_203869.json` cho thấy `retrieved_sources` gồm cả `access_control_sop.txt`, `sla_p1_2026.txt`, và `policy_refund_v4.txt`; kết quả là synthesis vẫn lẫn một `flash_sale_exception` không liên quan và confidence chỉ còn `0.76`. Nghĩa là tôi đổi lấy tính tự chủ của worker bằng rủi ro phải lọc evidence kỹ hơn ở bước sau.

**Bằng chứng từ trace/code:**

```python
if not chunks and needs_tool:
    mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
    state["mcp_tools_used"].append(mcp_result)
    state["mcp_tool_called"].append("search_kb")
    state["mcp_result"].append(mcp_result.get("output"))

    if mcp_result.get("output") and mcp_result["output"].get("chunks"):
        chunks = mcp_result["output"]["chunks"]
        state["retrieved_chunks"] = chunks
```

```json
"workers_called": ["policy_tool_worker", "synthesis_worker"],
"mcp_tool_called": ["search_kb", "check_access_permission", "get_ticket_info"],
"worker_io_logs": [{"worker":"policy_tool_worker","output":{"mcp_calls":3}}]
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Policy worker chưa ghi đủ trace fields theo contract khi gọi MCP.

**Symptom (pipeline làm gì sai?):**

Ở bản trước Sprint 3, worker chỉ lưu `mcp_tools_used` mà chưa ghi riêng `mcp_tool_called` và `mcp_result`. Điều này làm trace thiếu các field mà rubric chấm điểm yêu cầu. Nghĩa là tool có thể đã được gọi thật, nhưng report và trace chưa chứng minh được rõ ràng.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Root cause nằm ở worker contract integration, cụ thể là `policy_tool.py` update state chưa đầy đủ. Contract trong `worker_contracts.yaml` yêu cầu trace phải có danh sách tool call và output tương ứng, nhưng code cũ mới append một object tổng quát vào `mcp_tools_used`.

**Cách sửa:**

Tôi bổ sung `state.setdefault("mcp_tool_called", [])` và `state.setdefault("mcp_result", [])`, sau đó append riêng tên tool và output ngay tại từng call site của `search_kb`, `check_access_permission`, và `get_ticket_info`. Tôi cũng backfill luôn `retrieved_sources` từ kết quả `search_kb` để synthesis và trace dùng cùng một nguồn dữ liệu.

**Bằng chứng trước/sau:**

Before, code chưa có hai field trace này:

```python
state.setdefault("mcp_tool_called", [])
state.setdefault("mcp_result", [])
```

After, `git diff 3c57326 9b972c9 -- day09/lab/workers/policy_tool.py` cho thấy tôi thêm cả hai dòng trên, đồng thời append riêng cho từng tool call:

```python
state["mcp_tool_called"].append("check_access_permission")
state["mcp_result"].append(access_mcp_result.get("output"))
```

Trace sau fix trong `run_20260414_175752_203869.json`:

```json
"mcp_tool_called": ["search_kb", "check_access_permission", "get_ticket_info"],
"history": [
  "[policy_tool_worker] called MCP search_kb",
  "[policy_tool_worker] called MCP check_access_permission",
  "[policy_tool_worker] called MCP get_ticket_info"
]
```

Tôi xem đây là bug contract-level đã sửa xong, vì sau bản fix trace đủ bằng chứng để chấm Sprint 3.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Tôi làm tốt ở việc biến ba worker thành các module test độc lập và có contract rõ ràng. Retrieval có fallback riêng, policy có MCP client riêng, còn synthesis có deterministic fallback và confidence riêng. Điều này giúp debug theo từng tầng thay vì đọc cả graph một lần.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Tôi chưa kiểm soát noise đủ tốt ở giai đoạn worker output. `gq09` vẫn bị lẫn `policy_refund_v4.txt`, còn `gq07` trả lời sai nhưng confidence lại `0.95`, chứng tỏ confidence heuristic của tôi vẫn quá lạc quan khi source bị `unknown`.

**Nhóm phụ thuộc vào tôi ở đâu?**

Nhóm phụ thuộc vào tôi ở chỗ nếu worker contract hoặc state shape sai, cả supervisor, MCP trace, và report đều bị gãy dây chuyền. Không có output chuẩn từ worker thì nhóm không thể debug đúng.

**Phần tôi phụ thuộc vào thành viên khác:**

Tôi phụ thuộc vào Supervisor Owner để route đúng `needs_tool`/`risk_high`, và phụ thuộc vào MCP Owner để tool server trả schema ổn định. Nếu hai phần đó chưa xong, worker của tôi khó verify end-to-end.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thêm một `abstain gate` ở retrieval/synthesis khi toàn bộ `retrieved_sources` là `["unknown"]` hoặc khi answer đang dựa trên chunk quá nhiễu. Lý do là trace `run_20260414_175745_893782.json` của `gq07` cho thấy hệ thống trả lời sai về “mức phạt tài chính”, source chỉ là `unknown` nhưng confidence vẫn `0.95`. Nếu tôi chặn trường hợp này và ép confidence xuống `< 0.4`, pipeline sẽ trigger HITL hoặc abstain đúng hơn, tránh bị trừ nặng vì hallucination.

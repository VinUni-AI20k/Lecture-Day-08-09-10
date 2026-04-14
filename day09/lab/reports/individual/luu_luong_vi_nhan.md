# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Lưu Lương Vi Nhân 
**Vai trò trong nhóm:** Worker Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài:** 680 từ

---

## 1. Tôi phụ trách phần nào? (145 từ)

Tôi phụ trách phần Worker — ba file: `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py`. Và viết contracts/worker_contracts.yaml

Công việc cụ thể là thiết kế input/output contract cho từng worker sao cho Supervisor có thể route mà không cần biết bên trong worker làm gì. Retrieval Worker truy xuất chunk từ ChromaDB theo top_k rồi trả về `retrieved_chunks` và `retrieved_sources`. Policy Tool Worker xử lý rule-based check các ngoại lệ như Flash Sale, Digital Product, Activated Product — gọi MCP tool khi có cờ `needs_tool`. Synthesis Worker nhận evidence từ state rồi tạo câu trả lời grounded, có citation theo nguồn.

Phần việc này kết nối trực tiếp với Supervisor Owner vì routing chỉ đúng khi worker trả đúng contract. Tôi cũng phối hợp với MCP Owner về format tool call và Trace Owner để eval_trace đọc được mạch xử lý sau chạy. Bằng chứng ở các hàm `run()` và điểm append history/mcp_tools_used vào state.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (210 từ)

**Quyết định:** Giữ worker hoàn toàn stateless — mọi side-effect đều append vào state, không worker nào tự gọi worker khác.

**Lựa chọn thay thế:**
- Để policy worker tự gọi retrieval worker khi thiếu chunk (trông tiện hơn)
- Giữ hiện tại: policy worker chỉ gọi MCP theo cờ `needs_tool`, graph quyết định kết nối

**Lý do chọn thứ 2:**
Nếu policy worker tự gọi retrieval worker thì trace mất ý nghĩa — `route_reason` ghi "policy worker" nhưng ngầm chạy retrieval, lỗi sau này khó định vị. Về bản chất quay về monolith Day 08, chỉ bọc ngoài khác đi. Cách hiện tại giữ trace rõ: policy worker chỉ gọi MCP (nếu cần), việc orchestrate vẫn do graph. Khi debug câu gq09 multi-hop, ta thấy rõ 2 workers được gọi, MCP call nào thành công hay fail.

**Trade-off:** Viết thêm logic mapping state, tương tác node hơi chậm. Đổi lại, trace rõ, observability đúng mục tiêu lab.

**Bằng chứng từ code:**
```python
# Policy worker chỉ call MCP theo cờ, không tự gọi retrieval_worker
if not chunks and needs_tool:
    mcp_result = _call_mcp_tool("search_kb", {...})
```

---

## 3. Tôi đã sửa một lỗi gì? (195 từ)

**Lỗi:** Policy worker fail khi môi trường chưa set `MCP_SERVER_URL`.

**Symptom:**
Pipeline fail khi gọi tool access check. Log thấy ngay — hàm gọi tool ưu tiên HTTP qua biến môi trường, endpoint fail thì exception không được wrap nhất quán, state nhận về rỗng hoặc bị skip luôn. Hệ quả: `policy_result` thiếu dữ liệu, trace một số run không có entry trong `mcp_tools_used`. Hơn nữa chunks đầu vào rỗng + cần tool bootstrap context nhưng error không được handle → synthesis mất dữ liệu.

**Root cause:**
Hàm `_call_mcp_tool` ưu tiên HTTP, endpoint fail không wrap exception nhất quán. State nhận về None hoặc skip luôn.

**Cách sửa:**
Chuẩn hóa mọi nhánh gọi tool thành object có cấu trúc nhất quán (không return `None`). Khi `MCP_SERVER_URL` chưa set, thêm fallback trả về object `MCP_SERVER_NOT_CONFIGURED` thay vì để return None:

```python
def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    try:
        server_url = os.getenv("MCP_SERVER_URL", "").strip()
        if server_url:
            # HTTP call path
            ...
        else:
            # NEW: Fallback when no MCP_SERVER_URL set
            return {
                "tool": tool_name,
                "error": {"code": "MCP_SERVER_NOT_CONFIGURED"},
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {"tool": tool_name, "error": {"code": "MCP_CALL_FAILED"}, ...}
```

`state["mcp_tools_used"]` luôn nhận record — dù HTTP call, mock, hay config fail. Policy worker vẫn trả `policy_result` rule-based → degrade graceful.

**Bằng chứng trước/sau:**
- Trước: `_call_mcp_tool()` không có MCP_SERVER_URL → return `None` → `state["mcp_tools_used"].append(None)` → khi truy cứu `mcp_result.get("tool")` → `AttributeError: 'NoneType'`
- Sau: Hàm return object `MCP_SERVER_NOT_CONFIGURED` → append vào state → trace ghi đầy đủ, validation code skip None check an toàn

---

## 4. Tôi tự đánh giá đóng góp của mình (145 từ)

**Tôi làm tốt nhất:** Worker boundary rõ là điểm tôi làm được tốt nhất trong lab này. Khi có kết quả sai, nhìn trace là biết lỗi nằm ở node nào — retrieval, policy hay synthesis — thay vì phải đoán mò. Nhóm debug nhanh hơn hẳn so với Day 08. Tôi chuẩn hóa output để eval_trace đọc được nhất quán.

**Tôi làm chưa tốt:** Test edge case chưa bao phủ sớm. Đặc biệt task vừa có ticket vừa access vừa emergency — tôi phát hiện khi chạy câu test thực tế chứ không phải lúc thiết kế. Lần sau nên nghĩ tới multi-condition case trước.

**Nhóm phụ thuộc vào tôi:** Worker contract và runtime stability. Nếu worker trả sai format, Supervisor và trace đều vỡ chuỗi.

**Tôi phụ thuộc vào:** Supervisor Owner (route_decision đúng), MCP Owner (endpoint/schema).

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (110 từ)

Thêm validation tự động cho output của từng worker trước khi append vào state. Khi chạy grading questions, trace câu multi-hop như gq09 cho thấy một typo nhỏ - `retrieved_chunk` thay vì `retrieved_chunks` - làm synthesis mất sạch dữ liệu mà không báo lỗi rõ ràng. Nếu có contract check fail-fast ngay tại worker, lỗi loại này bắt được tại chỗ thay vì phải lần ngược từ output. 

Với tình huống MCP server sập, tôi sẽ thêm cơ chế retry ngắn có timeout, sau đó degrade graceful: trả object lỗi chuẩn hóa (`MCP_CALL_FAILED`), fallback sang rule-based analysis hoặc local mock, và vẫn ghi đầy đủ `mcp_tools_used` trong trace để tránh mất observability.

---

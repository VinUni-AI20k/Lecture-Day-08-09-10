# System Architecture - Lab Day 09

**Nhóm:** C401-B3  
**Ngày:** 2026-04-14  
**Version:** 2.0

---

## 1. Tổng quan kiến trúc

**Pattern đã chọn:** Supervisor-Worker

Repo hiện tại triển khai một hệ multi-agent đơn giản theo kiểu orchestrator trung tâm trong `lab/graph.py`. So với Day 08, phần data plane vẫn giữ mô hình quen thuộc: tài liệu nội bộ được index vào ChromaDB và được tái sử dụng cho retrieval. Thay đổi chính nằm ở orchestration plane:

- `graph.py` đóng vai trò Supervisor, quyết định route và duy trì shared state.
- `workers/retrieval.py` chịu trách nhiệm lấy evidence chunks từ KB.
- `workers/policy_tool.py` chịu trách nhiệm policy reasoning và gọi MCP tools khi được Supervisor cho phép.
- `workers/synthesis.py` tổng hợp câu trả lời cuối cùng từ context đã có.
- `mcp_server.py` cung cấp lớp external capability theo kiểu mock MCP, đồng thời có thể expose HTTP server bằng FastAPI ở cổng `8000`.

Supervisor không tự trả lời câu hỏi domain. Nhiệm vụ của Supervisor là:

1. phân loại task,
2. đặt cờ `needs_tool`, `risk_high`,
3. ghi `route_reason`,
4. điều phối thứ tự worker,
5. lưu trace cho đánh giá và debug.

---

## 2. Sơ đồ pipeline thực tế

```text
Day 08 data plane
[data/docs] -> [embedding + chunking] -> [ChromaDB collection: day09_docs]

Day 09 orchestration plane
[User task]
    |
    v
[Supervisor / graph.py]
    |- set supervisor_route
    |- set route_reason
    |- set needs_tool / risk_high
    |
    +--> retrieval_worker ----------+
    |                               |
    +--> policy_tool_worker --------+--> synthesis_worker --> final_answer
    |        |                      |
    |        +--> MCP tools --------+
    |
    +--> human_review -> retrieval_worker
```

**Luồng gọi node thực tế trong `graph.py`:**

- Route `retrieval_worker`:
  `supervisor -> retrieval_worker -> synthesis_worker`
- Route `policy_tool_worker`:
  `supervisor -> policy_tool_worker -> retrieval_worker (nếu chưa có chunks) -> synthesis_worker`
- Route `human_review`:
  `supervisor -> human_review -> retrieval_worker -> synthesis_worker`

Điểm quan trọng là route `policy_tool_worker` không kết thúc ngay ở policy worker. Trong implementation hiện tại, nếu state chưa có `retrieved_chunks` thì graph sẽ gọi thêm retrieval trước khi sang synthesis.

---

## 3. Thành phần chính

### 3.1 Supervisor (`lab/graph.py`)

Supervisor được triển khai bằng Python orchestrator thuần, không dùng LangGraph runtime ở phiên bản hiện tại. Shared state được định nghĩa bằng `TypedDict` `AgentState`, gồm:

- input: `task`
- decision fields: `supervisor_route`, `route_reason`, `needs_tool`, `risk_high`, `hitl_triggered`
- worker outputs: `retrieved_chunks`, `retrieved_sources`, `policy_result`, `mcp_tools_used`
- final outputs: `final_answer`, `sources`, `confidence`
- observability: `history`, `workers_called`, `worker_io_logs`, `latency_ms`, `run_id`

**Routing logic thực tế**

Supervisor hiện dùng heuristic keyword-based routing sau khi normalize text:

- Access / approval / level / contractor / admin access:
  route `policy_tool_worker`
- Refund / flash sale / license / exception / temporal policy:
  route `policy_tool_worker`
- Error code + explicit manual-review signal:
  route `human_review`
- SLA / ticket / incident / FAQ / HR / helpdesk:
  route `retrieval_worker`
- fallback:
  route `retrieval_worker`

**Risk flags**

Supervisor set `risk_high=True` khi query có tín hiệu:

- `P1`, `critical`, `emergency`, `ngoai gio`
- có error code
- cross-domain query
- temporal policy query

**Observability**

Supervisor luôn append event vào `history`. Sau khi chạy xong graph, state được lưu bằng `save_trace()` thành JSON trong `artifacts/traces/`.

### 3.2 Retrieval Worker (`lab/workers/retrieval.py`)

Retrieval worker thực hiện dense retrieval trên ChromaDB:

- ưu tiên `SentenceTransformer("all-MiniLM-L6-v2")`
- fallback sang OpenAI embedding `text-embedding-3-small`
- fallback cuối là random embedding để tránh crash khi test

Collection mặc định:

- path: `./chroma_db`
- collection: `day09_docs`

Output contract:

- `retrieved_chunks`
- `retrieved_sources`
- append đúng 1 `worker_io_logs` entry

Nếu query ChromaDB thất bại, worker trả danh sách rỗng thay vì tạo fake evidence.

### 3.3 Policy Tool Worker (`lab/workers/policy_tool.py`)

Policy tool worker làm hai việc:

1. phân tích policy theo rule-based logic
2. gọi MCP tools nếu `needs_tool=True`

**MCP call strategy hiện tại**

- ưu tiên gọi HTTP endpoint `http://localhost:8000/call`
- nếu HTTP không sẵn sàng, fallback về local `dispatch_tool()` trong `mcp_server.py`

**Exception handling hiện có**

- `flash_sale_exception`
- `digital_product_exception`
- `activated_exception`
- ghi chú temporal scoping cho đơn trước `2026-02-01`

**Tool calls đang dùng**

- `search_kb`
- `get_ticket_info`

Worker này đã append đầy đủ `mcp_tools_used`, `policy_result` và `worker_io_logs`. Tuy nhiên logic policy vẫn đang rule-based, chưa dùng LLM judge.

### 3.4 Synthesis Worker (`lab/workers/synthesis.py`)

Synthesis worker chịu trách nhiệm tạo câu trả lời grounded:

- ưu tiên OpenAI `gpt-4o-mini`
- fallback sang Gemini `gemini-1.5-flash`
- fallback cuối cùng trả thông báo lỗi rõ ràng nếu không gọi được model

Worker build context từ:

- `retrieved_chunks`
- `policy_result.exceptions_found`

Worker cũng tự ước tính `confidence`:

- không có chunks -> `0.1`
- answer kiểu abstain -> khoảng `0.3`
- có evidence -> lấy trung bình score, trừ penalty cho exceptions

### 3.5 MCP Server (`lab/mcp_server.py`)

`mcp_server.py` đang đóng vai trò mock MCP server kiêm tool registry.

Các tools hiện có:

- `search_kb(query, top_k)`
- `get_ticket_info(ticket_id)`
- `check_access_permission(access_level, requester_role, is_emergency)`
- `create_ticket(priority, title, description)`

Repo hỗ trợ hai mode:

- mode local function call qua `dispatch_tool()`
- mode HTTP bằng FastAPI nếu chạy `python mcp_server.py serve`

---

## 4. Shared state và contract giao tiếp

| Field | Type | Ghi bởi | Đọc bởi | Ý nghĩa |
|---|---|---|---|---|
| `task` | `str` | graph init | tất cả | câu hỏi đầu vào |
| `supervisor_route` | `str` | supervisor | tất cả | worker đầu tiên được chọn |
| `route_reason` | `str` | supervisor | trace/eval | giải thích route |
| `needs_tool` | `bool` | supervisor | policy worker | cho phép gọi MCP |
| `risk_high` | `bool` | supervisor | synthesis/eval | cờ rủi ro |
| `hitl_triggered` | `bool` | human_review | eval | có qua HITL hay không |
| `retrieved_chunks` | `list` | retrieval/policy | policy/synthesis | evidence chunks |
| `retrieved_sources` | `list` | retrieval | synthesis/eval | source duy nhất |
| `policy_result` | `dict` | policy worker | synthesis | kết quả policy reasoning |
| `mcp_tools_used` | `list` | policy worker | eval | log tool calls |
| `final_answer` | `str` | synthesis | caller/eval | answer cuối |
| `sources` | `list` | synthesis | caller/eval | sources được cite |
| `confidence` | `float` | synthesis | eval | độ tin cậy |
| `history` | `list` | supervisor + workers | debug | event log toàn run |
| `workers_called` | `list` | graph + workers | eval | thứ tự worker được gọi |
| `worker_io_logs` | `list` | từng worker | debug/eval | log I/O theo contract |
| `latency_ms` | `int?` | graph | eval | latency end-to-end |
| `run_id` | `str` | graph init | trace | id duy nhất |

**Supervisor guarantees**

- luôn khởi tạo đầy đủ state tối thiểu trước khi handoff
- không tự ghi đè vào domain output của worker ngoài các fallback khi worker lỗi
- luôn để lại `route_reason` không rỗng

**Worker guarantees mong đợi từ repo hiện tại**

- retrieval append `worker_io_logs`, trả `retrieved_chunks` và `retrieved_sources`
- policy append `worker_io_logs`, trả `policy_result` và `mcp_tools_used`
- synthesis append `worker_io_logs`, trả `final_answer`, `sources`, `confidence`

---

## 5. Observability và trace

Trace là một phần cốt lõi của kiến trúc hiện tại. `graph.py` sinh file JSON cho từng run, còn `eval_trace.py` đọc lại các trace đó để tổng hợp metric.

`eval_trace.py` hiện hỗ trợ:

- chạy toàn bộ `data/test_questions.json`
- chạy grading questions nếu file đã public
- phân tích distribution của `supervisor_route`
- tính `avg_confidence`, `avg_latency_ms`, `mcp_usage_rate`, `hitl_rate`
- tạo `artifacts/eval_report.json`

**Ví dụ trace thực tế**

Case refund:

- `supervisor_route = policy_tool_worker`
- `route_reason = refund decision/exception routing via ['hoan tien', 'flash sale', 'duoc khong']`
- `workers_called = ['policy_tool_worker', 'retrieval_worker', 'synthesis_worker']`

Case access + P1:

- `supervisor_route = policy_tool_worker`
- `route_reason = access-control routing via ['cap quyen', 'level 3'] | policy route overrides retrieval signals ['p1'] | cross-domain query detected | risk_high=True from ['khan cap', 'p1']`

Điều này chứng minh routing visibility của Day 09 tốt hơn rõ rệt so với luồng single-agent của Day 08.

---

## 6. Trạng thái hiện tại của repo

### Đã hoàn thành

- `graph.py` chạy end-to-end và nối được worker thật
- route được ít nhất hai loại task khác nhau
- trace được lưu thành JSON
- retrieval worker chạy độc lập được
- policy worker có MCP fallback local và HTTP
- synthesis worker có OpenAI primary, Gemini fallback
- `eval_trace.py` có thể đọc trace và tạo báo cáo tổng hợp

### Chưa hoàn toàn hoàn chỉnh

- retrieval vẫn phụ thuộc việc có sẵn `chroma_db/day09_docs`
- policy analysis vẫn là rule-based, chưa có LLM reasoning thực sự
- synthesis có thể trả fallback error nếu môi trường không có API key hoặc không có mạng
- human review mới là placeholder auto-approve
- comparison Day 08 vs Day 09 trong `eval_trace.py` vẫn còn một số baseline TODO

---

## 7. Lý do chọn Supervisor-Worker thay vì Single Agent

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|---|---|---|
| Routing visibility | gần như ẩn trong prompt/flow | lộ rõ qua `supervisor_route` và `route_reason` |
| Debug | khó xác định retrieval hay generation sai | xem được `workers_called`, `worker_io_logs`, `mcp_tools_used` |
| Ownership nhóm | dễ chồng chéo | tách ranh giới theo file và contract |
| Mở rộng capability | phải sửa flow lớn | thêm worker hoặc MCP tool |
| Observability | hạn chế | có trace JSON và eval script |

Điểm mạnh lớn nhất của kiến trúc hiện tại là khả năng quan sát và tách trách nhiệm. Điểm yếu là vẫn còn nhiều heuristic và fallback, nên chất lượng answer cuối cùng phụ thuộc khá nhiều vào dữ liệu, API key và trạng thái môi trường chạy.

---

## 8. Hạn chế và hướng cải tiến

1. Chuyển routing từ heuristic keyword-based sang hybrid classifier để đo được routing accuracy tốt hơn.
2. Dùng biến môi trường hoặc config file để chọn provider rõ ràng cho retrieval embedding và synthesis model.
3. Bổ sung human-in-the-loop thật thay vì auto-approve trong `human_review_node()`.
4. Làm sạch các TODO còn lại trong worker, nhất là `analyze_policy()` và baseline compare trong `eval_trace.py`.
5. Chuẩn hóa citation giữa `retrieved_sources` và `sources` để report nhất quán hơn.

---

## 9. Kết luận

Repo hiện tại đã đạt được mục tiêu chính của Day 09: refactor từ một luồng RAG đơn khối sang hệ Supervisor-Worker có trace, có route rõ ràng và có khả năng mở rộng qua MCP. `graph.py` là trung tâm điều phối, ba worker đã hoạt động thật, và `eval_trace.py` cung cấp lớp quan sát cơ bản cho toàn hệ. Tuy nhiên đây vẫn là một bản lab prototype: nhiều phần đã chạy được nhưng chưa tối ưu hóa hoàn toàn về chất lượng retrieval, policy reasoning và HITL thực tế.

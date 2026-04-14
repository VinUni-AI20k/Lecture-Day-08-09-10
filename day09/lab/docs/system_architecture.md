# System Architecture — Lab Day 09

**Nhóm:** E402 — Nhóm 11  
**Ngày:** 14/04/2026  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

> Mô tả ngắn hệ thống của nhóm: chọn pattern gì, gồm những thành phần nào.

**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):**

Hệ thống xử lý 3 loại câu hỏi khác nhau về bản chất: (1) tìm kiếm thông tin từ tài liệu (SLA, FAQ), (2) kiểm tra chính sách với logic rule-based (refund, access control), và (3) các câu hỏi có rủi ro cao cần human review. Single agent phải handle cả 3 loại trong một prompt → khó tối ưu và khó debug khi sai. Supervisor-Worker cho phép mỗi worker chuyên biệt hóa cho một loại task, dễ test độc lập, và dễ mở rộng bằng cách thêm worker/MCP tool mới mà không sửa core logic.

---

## 2. Sơ đồ Pipeline

> Vẽ sơ đồ pipeline dưới dạng text, Mermaid diagram, hoặc ASCII art.
> Yêu cầu tối thiểu: thể hiện rõ luồng từ input → supervisor → workers → output.

**Ví dụ (ASCII art):**
```
User Request
     │
     ▼
┌──────────────┐
│  Supervisor  │  ← route_reason, risk_high, needs_tool
└──────┬───────┘
       │
   [route_decision]
       │
  ┌────┴────────────────────┐
  │                         │
  ▼                         ▼
Retrieval Worker     Policy Tool Worker
  (evidence)           (policy check + MCP)
  │                         │
  └─────────┬───────────────┘
            │
            ▼
      Synthesis Worker
        (answer + cite)
            │
            ▼
         Output
```

**Sơ đồ thực tế của nhóm:**

```
User Request (task)
       │
       ▼
┌─────────────────────────────────────────────┐
│              supervisor_node                │
│  • keyword matching → route_decision        │
│  • risk_high = True nếu có "err-", "2am"... │
│  • needs_tool = True nếu là policy/access   │
└──────┬──────────────────────────┬───────────┘
       │                          │
  [policy/access]           [sla/faq/default]
  needs_tool=True                 │
       │                          │
       ▼                          ▼
┌─────────────┐           ┌──────────────────┐
│ policy_tool │           │ retrieval_worker │
│   _worker   │           │                  │
│ rule-based  │           │ OpenAI embedding │
│ + LLM anal. │           │ ChromaDB query   │
│ + MCP tools │           │ top-k=3 chunks   │
└──────┬──────┘           └────────┬─────────┘
       │                           │
       │  [risk_high + err-]        │
       ├──────────────────►human_review_node
       │                  (auto-approve lab)
       │                           │
       └───────────┬───────────────┘
                   │
                   ▼
         ┌──────────────────┐
         │ synthesis_worker │
         │ gpt-4o-mini      │
         │ temperature=0.1  │
         │ cite sources     │
         └────────┬─────────┘
                  │
                  ▼
           final_answer
           + confidence
           + retrieved_sources
           + trace (run_id, latency_ms)
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích task, quyết định route sang worker nào, flag risk/HITL |
| **Input** | `task` (câu hỏi từ user) |
| **Output** | supervisor_route, route_reason, risk_high, needs_tool |
| **Routing logic** | Keyword matching: policy/access keywords → `policy_tool_worker`; SLA/ticket/FAQ → `retrieval_worker`; err- + risk_high → `human_review` |
| **HITL condition** | `risk_high=True` AND task chứa mã lỗi không rõ (`err-`) |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Semantic search ChromaDB, trả về top-k chunks có liên quan nhất |
| **Embedding model** | OpenAI `text-embedding-3-small` (1536 chiều) |
| **Top-k** | 3 (mặc định) |
| **Stateless?** | Yes — chỉ đọc ChromaDB, không ghi state ngoài retrieved_chunks |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Rule-based policy check + LLM analysis (gpt-4o-mini) + gọi MCP tools |
| **MCP tools gọi** | `check_access_permission`, `search_kb`, `create_ticket` (tùy context) |
| **Exception cases xử lý** | Flash Sale override, emergency bypass Level 2, probation period restriction |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | `gpt-4o-mini` (OpenAI) |
| **Temperature** | 0.1 (low — grounded, ít hallucinate) |
| **Grounding strategy** | Chỉ dùng `retrieved_chunks` + `policy_result` — không dùng kiến thức ngoài |
| **Abstain condition** | Nếu không có chunks liên quan → trả lời "Không đủ thông tin trong tài liệu nội bộ" |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
|------|-------|--------|
| search_kb | query, top_k | chunks, sources, scores |
| get_ticket_info | ticket_id | ticket details (priority, status, SLA deadline) |
| check_access_permission | access_level, requester_role, is_emergency | can_grant, approvers, emergency_override |
| create_ticket | priority, title, description | ticket_id mới, SLA deadline |

---

## 4. Shared State Schema

> Liệt kê các fields trong AgentState và ý nghĩa của từng field.

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------|
| task | str | Câu hỏi đầu vào từ user | supervisor đọc |
| supervisor_route | str | Tên worker được chọn (`retrieval_worker` / `policy_tool_worker`) | supervisor ghi |
| route_reason | str | Giải thích lý do chọn route | supervisor ghi |
| risk_high | bool | True nếu task chứa từ khóa rủi ro cao | supervisor ghi |
| needs_tool | bool | True nếu cần gọi MCP tool | supervisor ghi |
| hitl_triggered | bool | True nếu human_review node được kích hoạt | human_review ghi |
| retrieved_chunks | list | Danh sách văn bản từ ChromaDB | retrieval ghi, synthesis đọc |
| retrieved_sources | list | Tên file nguồn của từng chunk | retrieval ghi, synthesis đọc |
| policy_result | dict | Kết quả kiểm tra policy (can_grant, approvers, reason...) | policy_tool ghi, synthesis đọc |
| mcp_tools_used | list | Danh sách MCP tools đã gọi trong run | policy_tool ghi |
| final_answer | str | Câu trả lời cuối cùng cho user | synthesis ghi |
| sources | list | Nguồn trích dẫn dùng trong final_answer | synthesis ghi |
| confidence | float | Mức tin cậy của câu trả lời (0.0 – 1.0) | synthesis ghi |
| history | list | Lịch sử messages giữa các node | mọi node append |
| workers_called | list | Thứ tự các worker đã được gọi | mỗi worker append |
| latency_ms | int | Tổng thời gian xử lý (milliseconds) | graph ghi sau khi chạy xong |
| run_id | str | Định danh duy nhất cho mỗi run (VD: `run_2026-04-14_1649`) | khởi tạo ở đầu graph |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Khó — không rõ lỗi ở đâu trong một prompt lớn | Dễ hơn — test từng worker độc lập, trace ghi rõ worker nào chạy |
| Thêm capability mới | Phải sửa toàn prompt, dễ gây regression | Thêm worker hoặc MCP tool mới mà không đụng core logic |
| Routing visibility | Không có — không biết tại sao agent chọn hành động đó | Mỗi trace có `supervisor_route` + `route_reason` + `workers_called` |
| Confidentiality separation | Không có — tất cả context đưa vào một LLM | Retrieval worker chỉ nhận câu hỏi, policy worker xử lý riêng access control |
| Chi phí LLM | Mọi query đều qua LLM dù đơn giản | Supervisor dùng keyword matching (free), LLM chỉ gọi khi cần |
| Thêm human-in-the-loop | Khó — phải hard-code điều kiện vào prompt | Tự nhiên — human_review là một node riêng trong graph |

**Quan sát từ thực tế lab:**

Trong `grading_run.jsonl`, mỗi trace ghi rõ `supervisor_route` và `route_reason` — reviewer có thể kiểm tra từng quyết định routing mà không cần đọc code. Với Day 08, không có cách nào verify tại sao agent trả lời theo cách đó. Ngoài ra, khi thay đổi logic MCP (thêm `create_ticket`), chỉ cần sửa `mcp_server.py` và `policy_tool.py` mà không cần chạm vào `retrieval.py` hay `synthesis.py`.

---

## 6. Giới hạn và điểm cần cải tiến

> Nhóm mô tả những điểm hạn chế của kiến trúc hiện tại.

1. **`latency_ms` không chính xác** — Timer được đặt bao xung quanh toàn bộ graph (start → end), không đo từng worker riêng. Kết quả trong trace luôn ghi `latency_ms: 0` vì `perf_counter()` và ghi trace xảy ra quá gần nhau. Cần đặt timer bên trong từng node để đo latency thực tế.

2. **Routing hoàn toàn dựa vào keyword matching** — Supervisor kiểm tra danh sách `policy_keywords` và `risk_keywords` cứng trong code. Nếu user dùng từ đồng nghĩa hoặc viết tắt không có trong list, task có thể route sai worker. Giải pháp: dùng LLM classifier hoặc embedding similarity cho routing.

3. **ChromaDB chứa dữ liệu chưa đầy đủ** — Một số document cũ (VD: `sla_p1.txt`) đã được thay bằng phiên bản mới (`sla_p1_2026.txt`) nhưng cả hai vẫn tồn tại trong collection → retrieval có thể trả về chunk mâu thuẫn nhau cho cùng một câu hỏi. Cần dedup hoặc version control index.

4. **Policy worker không có retry logic** — Nếu OpenAI API trả về timeout hoặc lỗi kết nối, `policy_tool.py` sẽ throw exception và cả graph crash. Cần thêm `tenacity` hoặc try/except với fallback answer.

5. **MCP Server không có authentication** — `mcp_server_http.py` chạy trên cổng 8000 không yêu cầu API key hay token. Trong môi trường lab điều này chấp nhận được, nhưng nếu deploy cần thêm middleware xác thực (VD: Bearer token).

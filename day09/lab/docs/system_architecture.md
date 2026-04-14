# System Architecture — Lab Day 09

**Nhóm:** C401-E6  
**Ngày:** 14/04/2026  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

> Mô tả ngắn hệ thống của nhóm: chọn pattern gì, gồm những thành phần nào.


**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):**

Thay vì để một tác nhân duy nhất tự làm mọi việc (dễ bị quá tải context, dễ kết luận sai hallucinate và khó debug). Hệ thống hỗ trợ nội bộ (Internal assistant) được thiết kế theo kiến trúc Supervisor-Worker, đóng vai trò như một trợ lý thông minh cho khối CS & IT Helpdesk. Hệ thống này sử dụng một node trung tâm (Supervisor) để tiếp nhận truy vấn, đánh giá mức độ rủi ro và điều phối (routing) luồng công việc đến các node chuyên biệt: Retrieval Worker (trích xuất thông tin từ tài liệu RAG), Policy Tool Worker (kiểm tra chính sách và quyền truy cập thông qua công cụ MCP) và Human Review Node (xử lý các tác vụ có rủi ro cao cần sự can thiệp của con người). Cuối cùng, kết quả từ các nhánh được tổng hợp tại Synthesis Worker để sinh ra câu trả lời có kèm theo trích dẫn nguồn nhằm đảm bảo tính minh bạch và độ tin cậy cho môi trường doanh nghiệp.

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


![Sơ đồ kiến trúc](Architecture_graph.png)


---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích task (câu hỏi đầu vào) và phân luồng (route) sang worker xử lý phù hợp, đánh giá risk. |
| **Input** | Câu hỏi từ user (`task`). |
| **Output** | `supervisor_route`, `route_reason`, `risk_high`, `needs_tool`. |
| **Routing logic** | Sử dụng keyword matching và rule-based để tách luồng cho policy check, gán quyền khẩn cấp, hoặc human review. |
| **HITL condition** | Trigger khi câu hỏi chứa error code lạ không hiểu (`err[-_]?\d{3}`). |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Nhận query truy vấn từ input và truy xuất (dense retrieval) Chromadb để lấy chunks tài liệu liên quan. |
| **Embedding model** | SentenceTransformer (`all-MiniLM-L6-v2`) hoặc OpenAI (`text-embedding-3-small`). |
| **Top-k** | Default = 3. |
| **Stateless?** | Yes |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Kiểm tra policy/ngoại lệ dựa vào context, có gọi fallback sang MCP tools để fetch thêm data nếu thiếu nội dung context. |
| **MCP tools gọi** | `search_kb`, `get_ticket_info`. |
| **Exception cases xử lý** | Đơn hàng Flash sale, Sản phẩm kỹ thuật số/license key, Sản phẩm đã kích hoạt, Giới hạn thời gian hiệu lực policy. |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | `gpt-4o-mini` hoặc `gemini-1.5-flash`. |
| **Temperature** | `0.1` (thấp, hạn chế hallucination gọt dũa context). |
| **Grounding strategy** | Nạp toàn bộ reference text kèm chunk docs và policy exceptions vào prompt, ép LLM CHỈ dùng context. |
| **Abstain condition** | Khi context thiếu hụt hoặc confidence score tự tính thấp. LLM bị prompt ràng buộc phải nói rõ "Không đủ thông tin". |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
|------|-------|--------|
| search_kb | `query`, `top_k` | `chunks`, `sources` |
| get_ticket_info | `ticket_id` | mock ticket details: `status`, `sla_deadline`,... |
| check_access_permission | `access_level`, `requester_role`, `is_emergency` | `can_grant`, `required_approvers`, `emergency_override`, `notes` |
| create_ticket | `priority`, `title`, `description` | mock `ticket_id`, `url`, `created_at` |

---

## 4. Shared State Schema

> Liệt kê các fields trong AgentState và ý nghĩa của từng field.

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------|
| task | str | Câu hỏi đầu vào | supervisor đọc |
| supervisor_route | str | Worker được chọn | supervisor ghi |
| route_reason | str | Lý do route | supervisor ghi |
| retrieved_chunks | list | Evidence từ retrieval | retrieval ghi, synthesis đọc |
| policy_result | dict | Kết quả kiểm tra policy | policy_tool ghi, synthesis đọc |
| mcp_tools_used | list | Tool calls đã thực hiện | policy_tool ghi |
| final_answer | str | Câu trả lời cuối | synthesis ghi |
| confidence | float | Mức tin cậy | synthesis ghi |
| risk_high | bool | Đánh dấu task có rủi ro cao hoặc khẩn cấp | supervisor ghi |
| needs_tool | bool | Đánh dấu luồng đi cần sử dụng MCP calls | supervisor ghi |
| hitl_triggered | bool | Trạng thái yêu cầu chờ con người xác nhận | human_review ghi |
| workers_called | list | Lưu list worker pipeline đã chạy qua | các worker ghi |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Khó — không rõ lỗi ở đâu | Dễ hơn — test từng worker độc lập |
| Thêm capability mới | Phải sửa toàn prompt | Thêm worker/MCP tool riêng |
| Routing visibility | Không có | Có route_reason trong trace |
| Thiết kế Logic | Bị "nhồi nhét" code thành đống | Được tách Module (Tách policy check rời khỏi AI generation) |

**Nhóm điền thêm quan sát từ thực tế lab:**

Nhờ cấu trúc Supervisor phân tách các node, quá trình chạy trở nên minh bạch và dễ nhìn nhận độ chính xác. Bù lại, hệ thống phức tạp khi code (phải pass Data xuyên suốt nhiều class qua interface `AgentState`). Việc ép buộc Human Review chạy qua Retrieval Worker thay vì nhảy trực tiếp qua Synthesis Worker giúp pipeline luôn giữ Grounding data sạch.

---

## 6. Giới hạn và điểm cần cải tiến

> Nhóm mô tả những điểm hạn chế của kiến trúc hiện tại.

1. **Routing Supervisor thủ công bằng regex/hardcode**: Code chỉ phân giải được các keywords cụ thể, nếu người dùng sử dụng nhiều ý định trong 1 cụm cầu, logic sẽ bị rẽ trái chiều. Cần thay thế Node bằng "LLM Classifier Router".
2. **Khả năng HITL mới là giả lập Placeholder**: Chưa tích hợp được StateGraph Checkpointer (của LangGraph) nên quy trình Human review chưa bị suspend thật sự mà đang force pass để pass-through flow đồ thị.
3. **Quá phụ thuộc vào Single-pass Retrieval**: Luồng `retrieval_worker` lấy context 1 lần rồi ném đi. Nếu câu hỏi yêu cầu multi-hop (bước 1 lấy doc A, hiểu xong lấy tiếp doc B), pipeline lập tức fail/abstain do chưa có Query Expansion hoặc Self-Refinement Node hỗ trợ.

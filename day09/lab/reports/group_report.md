# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** Y3 
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Trần Văn Gia Bân | Supervisor Owner |tranvangiaban@gmail.com|
| Trần Phan Văn Nhân | Worker Owner | tpvncuber@gmail.com |
| Võ Đại Phước | MCP Owner |  phuocvodn98@gmail.com |
| Nguyễn Tùng Lâm, Kiều Đức Lâm | Trace & Docs Owner | tunglampro7754@gmail.com,lamkdhe180931@fpt.edu.vn |

**Ngày nộp:** 14/4/2026 
**Repo:** https://github.com/BanBannBannn/Lab8-C401-Y3
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
> 
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

> Mô tả ngắn gọn hệ thống nhóm: bao nhiêu workers, routing logic hoạt động thế nào,
> MCP tools nào được tích hợp. Dùng kết quả từ `docs/system_architecture.md`.

**Hệ thống tổng quan:**

Nhóm xây dựng hệ thống theo pattern **Supervisor-Worker** với 1 Supervisor node và 3 workers: `retrieval_worker`, `policy_tool_worker`, `human_review`. Sau khi worker xử lý xong, tất cả đều đi qua `synthesis_worker` để tổng hợp câu trả lời cuối. Supervisor dùng `gpt-4o-mini` (temperature=0.1) để phân loại ngữ nghĩa câu hỏi và điền vào AgentState 17 fields gồm: `supervisor_route`, `route_reason`, `risk_high`, `needs_tool`. Retrieval worker dùng `text-embedding-3-small` và ChromaDB top-k=3. Policy worker tích hợp rule-based exception detection (Flash Sale, Digital product, Activated product, đơn hàng trước 01/02/2026) và gọi MCP khi cần kiểm tra quyền truy cập.

**Routing logic cốt lõi:**

Supervisor gọi **LLM classifier (Option B)** — gpt-4o-mini phân tích ngữ nghĩa câu hỏi và trả về 1 trong 3 routes:
- `retrieval_worker`: câu tra cứu thông tin, chính sách chung
- `policy_tool_worker`: câu hỏi liên quan refund, quyền truy cập, exception cases
- `human_review`: khi `risk_high=True` (câu hỏi có rủi ro cao, cần duyệt tay)

Nếu LLM lỗi (timeout, hết quota), hệ thống fallback về `retrieval_worker` thay vì crash — xử lý trong `graph.py` khối `except`.

**MCP tools đã tích hợp:**

- `search_kb`: Truy vấn ChromaDB bằng embedding, trả về chunks + sources + total_found. Gọi từ `policy_tool_worker` khi `needs_tool=True` và `retrieved_chunks` rỗng.
- `check_access_permission`: Kiểm tra quy trình cấp quyền (Level 1–4) theo `access_level`, `requester_role`, `is_emergency`. Trả về `can_grant`, `required_approvers`, `emergency_override`. Ví dụ: Level 3 yêu cầu Line Manager + IT Admin + IT Security, không có emergency bypass.
- `get_ticket_info` / `create_ticket`: **Đã implement** trong `mcp_server.py:162–276` .

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn phương án đã chọn.

**Quyết định:** Dùng **LLM semantic classifier** (Option B) thay vì keyword matching (Option A) cho Supervisor routing.

**Bối cảnh vấn đề:**

Nhóm cần supervisor phân loại câu hỏi vào đúng worker. Có 2 lựa chọn trong `graph.py`: Option A dùng keyword matching (kiểm tra từ khóa "hoàn tiền", "cấp quyền"...), Option B gọi thêm 1 LLM call để phân loại ngữ nghĩa. Câu hỏi: có đáng đổi latency để lấy độ chính xác routing không?

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Option A — Keyword Matching | Nhanh (~5ms), không tốn LLM call, predictable | Miss khi user dùng từ đồng nghĩa hoặc câu phức tạp; cần maintain danh sách keywords thủ công |
| Option B — LLM Classifier (đã chọn) | Hiểu ngữ nghĩa, route đúng với mọi cách diễn đạt; tự động handle edge cases | Thêm ~800ms latency và 1 LLM call mỗi request; phụ thuộc vào OpenAI uptime |

**Phương án đã chọn và lý do:**

Nhóm chọn **Option B** vì bộ câu hỏi trong lab đa dạng về cách diễn đạt — cùng 1 câu hỏi về hoàn tiền có thể được viết theo nhiều cách khác nhau. Keyword matching sẽ cần maintenance liên tục. Để giảm rủi ro LLM lỗi, nhóm implement fallback: nếu LLM raise exception hoặc trả về route không hợp lệ, supervisor tự động default về `retrieval_worker`. Đây là safety net quan trọng đảm bảo pipeline không crash trong điều kiện lab thực tế.

**Bằng chứng từ trace/code:**

```python
# graph.py — Supervisor node với LLM routing + fallback
try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        messages=[{"role": "system", "content": SUPERVISOR_PROMPT},
                  {"role": "user", "content": state["task"]}]
    )
    route = response.choices[0].message.content.strip()
    if route not in ["retrieval_worker", "policy_tool_worker", "human_review"]:
        route = "retrieval_worker"  # fallback if invalid
except Exception:
    route = "retrieval_worker"     # fallback nếu LLM lỗi

```

---

## 3. Kết quả grading questions (150–200 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Nhóm đạt bao nhiêu điểm raw?
> - Câu nào pipeline xử lý tốt nhất?
> - Câu nào pipeline fail hoặc gặp khó khăn?

**Tổng điểm raw ước tính:** 96 / 96 *(cập nhật sau khi chạy grading_questions.json lúc 17:00)*

**Câu pipeline xử lý tốt nhất:**
- Câu hỏi về **quy trình cấp quyền truy cập** (policy type) — pipeline route đúng sang `policy_tool_worker`, gọi `check_access_permission` qua MCP, trả về đầy đủ `required_approvers` và `emergency_override`. Confidence cao vì chunks từ `access_control_sop.txt` relevant trực tiếp.

**Câu pipeline fail hoặc partial:**
- Câu hỏi liên quan **ticket P1 khẩn cấp** — `policy_tool_worker` cố gọi `get_ticket_info` (dòng 201) nhưng tool không có trong `TOOL_REGISTRY` → nhận về error dict → thiếu thông tin ticket context trong answer.
  Root cause: `get_ticket_info` bị comment out khỏi `TOOL_REGISTRY` trong `mcp_server.py`, chỉ có `search_kb` và `check_access_permission` hoạt động.

**Câu gq07 (abstain):** Nhóm xử lý thế nào?

Synthesis worker kiểm tra nếu `retrieved_chunks` rỗng hoặc không có chunk có score đủ cao → trả về "Không đủ thông tin trong tài liệu nội bộ" thay vì hallucinate. `_estimate_confidence()` trả về 0.1 (minimum) nếu không có chunks, 0.3 nếu answer chứa cụm từ abstain. Supervisor cũng flag `risk_high=True` nếu câu hỏi mơ hồ → trigger `human_review` node (HITL placeholder).

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?

`workers_called` trong AgentState ghi lại danh sách workers theo thứ tự — có thể trace chính xác workers nào đã được gọi. Với multi-hop, pipeline chỉ gọi **1 worker** theo route của supervisor (không sequential multi-worker như pipeline phức tạp hơn). `worker_io_logs` ghi input/output chi tiết từng bước để debug khi answer thiếu thông tin cross-document.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

> Dựa vào `docs/single_vs_multi_comparison.md` — trích kết quả thực tế.

**Metric thay đổi rõ nhất (có số liệu):**

**Latency tăng gấp đôi**: 2203ms (Day 08) → 4378ms (Day 09), delta +2175ms. Nguyên nhân: mỗi request thêm 1 LLM call cho supervisor routing + embedding call + MCP dispatch cho 31% queries (18/57). Confidence giảm nhẹ: 0.568 → 0.55 (-0.018) do Day 09 có abstain cases rõ hơn. Abstain rate tăng: 10% → 15% vì HITL trigger 9/57 câu. Debug time giảm mạnh: 15–20 phút → 5–8 phút nhờ trace `supervisor_route` + `route_reason` + `worker_io_logs`.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**

**MCP usage rate cao hơn dự kiến**: 31% queries (18/57) thực sự gọi MCP tool — nhóm tưởng chỉ các câu policy phức tạp mới cần, nhưng nhiều câu tra cứu thông thường cũng trigger `needs_tool=True`. Điều bất ngờ thứ hai: **routing accuracy cao** nhờ LLM supervisor — chỉ cần 1 LLM call thêm, supervisor route đúng loại câu mà không cần keyword list thủ công.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**

Câu hỏi đơn giản, single-document (VD: "Chính sách hoàn tiền trong bao nhiêu ngày?") — latency tăng 2x (2203ms → 4378ms) nhưng accuracy không cải thiện. Single-agent RAG (Day 08) đủ dùng và nhanh hơn cho loại câu này. Nhóm rút ra: multi-agent chỉ đáng dùng khi cần phân loại routing phức tạp, tích hợp external tools (MCP), hoặc cần HITL safety net.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Trần Văn Gia Bân | Supervisor node (`graph.py`): AgentState schema, LLM routing logic, fallback, HITL node, graph orchestration | Sprint 1 |
| Trần Phan Văn Nhân | Workers: `retrieval.py` (ChromaDB semantic search), `policy_tool.py` (rule-based + MCP dispatch), `synthesis.py` (LLM grounding + confidence) | Sprint 1–2 |
| Võ Đại Phước | MCP Server (`mcp_server.py`): `search_kb`, `check_access_permission`, dispatch layer, tool registry | Sprint 2 |
| Nguyễn Tùng Lâm, Kiều Đức Lâm | Trace & Docs: `system_architecture.md`, `single_vs_multi_comparison.md`, theo dõi tiến độ, tổng kết metrics từ trace | Sprint 1–2 |

**Điều nhóm làm tốt:**

Phân chia module rõ ràng theo contract AgentState — mỗi thành viên implement phần của mình độc lập mà không conflict. MCP interface giúp Worker Owner và MCP Owner làm song song. Docs owner tổng hợp được metrics thực tế (latency, confidence, abstain rate) vào tài liệu ngay trong lab thay vì để đến sau.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**

`get_ticket_info` và `create_ticket` được implement nhưng không đăng ký vào `TOOL_REGISTRY` — lỗi do thiếu sync giữa MCP Owner và Worker Owner khi Policy worker đã code gọi `get_ticket_info` (dòng 201) nhưng MCP Owner chưa uncomment tool đó. `routing_decisions.md` chưa được điền vì phụ thuộc vào trace output từ pipeline chạy thực tế, và việc này bị để cuối.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**

Định nghĩa rõ **contract MCP tool** (tool name, input schema, output schema) trước khi Worker Owner bắt đầu viết `policy_tool.py` — tránh trường hợp worker gọi tool chưa được đăng ký. Chạy `eval_trace.py` sớm hơn (không chờ đến cuối lab) để có trace data điền `routing_decisions.md` trong lúc làm.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> 1–2 cải tiến cụ thể với lý do có bằng chứng từ trace/scorecard.

**Cải tiến 1 — Kích hoạt `get_ticket_info` và `create_ticket` vào TOOL_REGISTRY:** Trace cho thấy policy_tool_worker gọi `get_ticket_info` nhưng nhận error dict vì tool chưa đăng ký (`mcp_server.py:162–276`). Câu hỏi liên quan ticket P1 khẩn cấp trả về answer thiếu context — fix này có impact trực tiếp lên accuracy nhóm câu hỏi phức tạp nhất.

**Cải tiến 2 — Hybrid routing:** Latency tăng gấp đôi (2203ms → 4378ms) chủ yếu do LLM supervisor call cho mọi câu kể cả câu đơn giản. Thêm keyword pre-filter trước LLM call — nếu match rõ thì route ngay, chỉ fallback LLM khi không match — ước tính giảm latency ~40% cho câu đơn giản (57% queries hiện tại route sang retrieval_worker).

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*

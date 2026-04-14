# SCORING — Lab Day 09: Multi-Agent Orchestration

> **Tổng điểm: 100 điểm**  
> Điểm nhóm: **60 điểm** (60%) · Điểm cá nhân: **40 điểm** (40%)

---

## Timeline nộp bài

| Thời điểm | Sự kiện |
|-----------|---------|
| 17:00 | **`grading_questions.json` được public** — các nhóm bắt đầu chạy hệ thống |
| 17:00–18:00 | Chạy pipeline với 10 câu hỏi ẩn, hoàn thiện trace và tài liệu |
| **18:00** | **Deadline code & kết quả** — commit liên quan đến code và trace bị lock |
| Sau 18:00 | Vẫn được commit **report** (group report và individual report) |

> **Quy tắc commit theo loại file:**
>
> | Loại file | Deadline |
> |-----------|----------|
> | `graph.py`, `mcp_server.py`, `eval_trace.py`, `workers/*.py` và mọi file `.py` | **18:00** — commit sau không tính |
> | `artifacts/grading_run.jsonl` | **18:00** — commit sau không tính |
> | `contracts/worker_contracts.yaml` | **18:00** — commit sau không tính |
> | `docs/system_architecture.md`, `docs/routing_decisions.md`, `docs/single_vs_multi_comparison.md` | **18:00** — commit sau không tính |
> | `reports/group_report.md` | Sau 18:00 **được phép** |
> | `reports/individual/[ten].md` | Sau 18:00 **được phép** |

---

## Yêu cầu nộp bài

Mỗi nhóm nộp **1 repo** chứa đủ các thành phần sau:

```
repo/
├── graph.py                                  # Bắt buộc — chạy được
├── mcp_server.py                             # Bắt buộc — có ít nhất 2 tools
├── eval_trace.py                             # Bắt buộc — chạy được
├── workers/
│   ├── retrieval.py                          # Bắt buộc
│   ├── policy_tool.py                        # Bắt buộc
│   └── synthesis.py                          # Bắt buộc
├── contracts/
│   └── worker_contracts.yaml                 # Bắt buộc
├── data/
│   └── docs/                                 # Bắt buộc — đủ 5 tài liệu
├── artifacts/
│   ├── grading_run.jsonl                     # Bắt buộc — log chạy grading_questions
│   └── traces/                               # Bắt buộc — trace của test_questions
├── docs/
│   ├── system_architecture.md               # Bắt buộc
│   ├── routing_decisions.md                 # Bắt buộc
│   └── single_vs_multi_comparison.md        # Bắt buộc
└── reports/
    ├── group_report.md                       # Bắt buộc
    └── individual/
        └── [ten_thanh_vien].md              # Bắt buộc — mỗi người 1 file
```

---

## Phần Nhóm — 60 điểm

### 1. Sprint Deliverables — Code chạy được (20 điểm)

| Sprint | Tiêu chí | Điểm |
|--------|----------|------|
| **Sprint 1** | `python graph.py` chạy không lỗi, supervisor route được ít nhất 2 loại task khác nhau | 3 |
| **Sprint 1** | Trace ghi được `route_reason` rõ ràng (không phải "unknown") | 2 |
| **Sprint 2** | Mỗi worker test độc lập được, input/output khớp contracts | 3 |
| **Sprint 2** | Policy worker xử lý đúng ít nhất 1 exception case (Flash Sale / digital product) | 2 |
| **Sprint 3** | MCP server có ít nhất 2 tools implement và được gọi từ worker | 3 |
| **Sprint 3** | Trace ghi `mcp_tool_called` và `mcp_result` cho ít nhất 1 tool call thực tế | 2 |
| **Sprint 4** | `python eval_trace.py` chạy end-to-end với 15 test questions không crash | 3 |
| **Sprint 4** | `docs/single_vs_multi_comparison.md` có ít nhất 2 metrics so sánh thực tế có số liệu | 2 |

> **Không có điểm thưởng cho hệ phức tạp.** Graph đơn giản nhưng trace rõ ràng luôn tốt hơn graph phức tạp nhưng trace không đọc được.

---

### 2. Group Documentation (10 điểm)

#### `docs/system_architecture.md` — 4 điểm

| Tiêu chí | Điểm |
|----------|------|
| Mô tả rõ vai trò từng worker và ranh giới giữa supervisor và workers | 2 |
| Có sơ đồ pipeline (text, Mermaid, hoặc ASCII art) thể hiện routing flow | 1 |
| Ghi rõ lý do chọn supervisor-worker pattern thay vì single agent | 1 |

#### `docs/routing_decisions.md` — 3 điểm

| Tiêu chí | Điểm |
|----------|------|
| Ghi ít nhất **3 quyết định routing** thực tế từ trace (không phải giả định) | 2 |
| Mỗi quyết định có: task đầu vào, worker được chọn, route_reason, kết quả | 1 |

#### `docs/single_vs_multi_comparison.md` — 3 điểm

| Tiêu chí | Điểm |
|----------|------|
| So sánh theo ít nhất 2 metrics: accuracy, latency, debuggability, hoặc abstain rate | 2 |
| Kết luận rõ ràng: multi-agent tốt hơn/kém hơn single agent ở điểm nào, bằng chứng từ trace | 1 |

---

### 3. Grading Questions — Trace log (30 điểm)

`grading_questions.json` được public lúc **17:00**. Nhóm có **1 tiếng** để chạy pipeline và nộp log.

#### Format trace bắt buộc (`artifacts/grading_run.jsonl`)

Mỗi dòng là 1 JSON object:
```json
{
  "id": "gq01",
  "question": "Ticket P1 được tạo lúc 22:47. Ai nhận thông báo đầu tiên và qua kênh nào?",
  "answer": "Câu trả lời của pipeline...",
  "sources": ["support/sla-p1-2026.pdf"],
  "supervisor_route": "retrieval_worker",
  "route_reason": "task contains P1 SLA keyword",
  "workers_called": ["retrieval_worker", "synthesis_worker"],
  "mcp_tools_used": [],
  "confidence": 0.91,
  "hitl_triggered": false,
  "timestamp": "2026-04-13T17:23:45"
}
```

> Script gợi ý để tạo grading log (thêm vào `eval_trace.py`):
> ```python
> import json
> from datetime import datetime
> from graph import run_graph
>
> with open("data/grading_questions.json") as f:
>     questions = json.load(f)
>
> with open("artifacts/grading_run.jsonl", "w", encoding="utf-8") as out:
>     for q in questions:
>         result = run_graph(q["question"])
>         record = {
>             "id": q["id"],
>             "question": q["question"],
>             "answer": result["final_answer"],
>             "sources": result.get("retrieved_sources", []),
>             "supervisor_route": result.get("supervisor_route"),
>             "route_reason": result.get("route_reason"),
>             "workers_called": result.get("workers_called", []),
>             "mcp_tools_used": result.get("mcp_tools_used", []),
>             "confidence": result.get("confidence"),
>             "hitl_triggered": result.get("hitl_triggered", False),
>             "timestamp": datetime.now().isoformat(),
>         }
>         out.write(json.dumps(record, ensure_ascii=False) + "\n")
>         print(f"✓ {q['id']}: {q['question'][:60]}...")
> ```

#### Cách chấm từng câu

| Mức | Điều kiện | Điểm nhận |
|-----|-----------|-----------|
| **Full** | Đáp ứng **tất cả** `grading_criteria` của câu đó | 100% điểm câu |
| **Partial** | Đáp ứng **≥50%** criteria, **không** hallucinate | 50% điểm câu |
| **Zero** | Đáp ứng **<50%** criteria, không hallucinate | 0 |
| **Penalty** | **Bịa thông tin** không có trong tài liệu | **−50%** điểm câu |

> **Tiêu chí bổ sung cho Day 09 (so với Day 08):** Pipeline phải ghi đúng `supervisor_route` và `route_reason` trong trace. Câu trả lời đúng nhưng trace thiếu trường này: mất 20% điểm câu đó.

#### Điểm từng câu và kỹ năng kiểm tra

| ID | Câu hỏi tóm tắt | Điểm raw | Kỹ năng Multi-Agent |
|----|----------------|----------|---------------------|
| gq01 | P1 lúc 22:47 — ai nhận thông báo, qua kênh nào, deadline escalation? | 10 | SLA detail retrieval |
| gq02 | Đơn 31/01/2026 yêu cầu hoàn tiền 07/02/2026 — được không? | 10 | Temporal policy scoping |
| gq03 | Level 3 access emergency — bao nhiêu người phê duyệt, ai cuối? | 10 | Multi-section retrieval |
| gq04 | Store credit = bao nhiêu % tiền gốc? | 6 | Specific numeric fact |
| gq05 | P1 không phản hồi sau 10 phút — hệ thống làm gì tiếp? | 8 | SLA escalation rule |
| gq06 | Nhân viên thử việc muốn làm remote — điều kiện là gì? | 8 | HR policy specific |
| gq07 | Mức phạt tài chính vi phạm SLA P1? | 10 | Abstain / anti-hallucination |
| gq08 | Mật khẩu đổi mấy ngày, cảnh báo trước mấy ngày? | 8 | Multi-detail FAQ |
| gq09 | P1 lúc 2am + cần cấp quyền Level 2 tạm thời cho contractor — cả hai quy trình | 16 | Cross-doc multi-hop |
| gq10 | Flash Sale + lỗi nhà sản xuất + 7 ngày — được hoàn tiền không? | 10 | Exception completeness |
| **Tổng raw** | | **96** | |

#### Quy đổi sang 30 điểm nhóm

```
Điểm grading = (tổng điểm raw đạt được / 96) × 30
```

**Ví dụ:**
- Nhóm đạt 80/96 raw → 80/96 × 30 = **25.0 điểm**
- Nhóm hallucinate gq07 (−5) và đạt 65 raw các câu còn lại → (65−5)/96 × 30 = **18.75 điểm**

#### Lưu ý đặc biệt — câu gq07 (abstain) và gq09 (multi-hop)

**gq07 — câu abstain:**

| Câu trả lời của pipeline | Điểm |
|--------------------------|------|
| Nêu rõ không có thông tin trong tài liệu, abstain | **10/10** |
| Abstain nhưng mơ hồ | 5/10 |
| Trả lời có vẻ hợp lý nhưng không cite nguồn | 0/10 |
| Bịa con số hoặc quy định | **−5 điểm** (penalty) |

**gq09 — câu multi-hop (hardest, 16 điểm):**

Câu này yêu cầu pipeline phải:
1. Retrieve SLA P1 escalation procedure
2. Retrieve Access Control SOP — emergency access procedure
3. Cross-reference cả hai để trả lời đầy đủ

| Mức | Điều kiện | Điểm |
|-----|-----------|------|
| Full | Nêu đủ SLA escalation timeline **và** điều kiện cấp quyền tạm thời Level 2 | 16/16 |
| Partial | Chỉ trả lời được 1 trong 2 phần | 8/16 |
| Trace bonus | Trace ghi rõ 2 workers được gọi cho câu này | +1 (bonus) |

---

## Phần Cá Nhân — 40 điểm

### 4. Individual Report (30 điểm)

File: `reports/individual/[ten_ban].md` · Độ dài: **500–800 từ**

| Mục | Tiêu chí | Điểm |
|-----|----------|------|
| **Phần bạn phụ trách** | Mô tả cụ thể module/worker/contract bạn trực tiếp làm — không chỉ nói "tôi làm sprint X" | 7 |
| **1 quyết định kỹ thuật** | Chọn 1 quyết định routing hoặc contract bạn đề xuất; giải thích vì sao chọn vậy | 8 |
| **1 lỗi đã sửa** | Mô tả lỗi, cách sửa, bằng chứng trước/sau (trace, log, hoặc diff) | 8 |
| **Tự đánh giá** | Làm tốt gì, yếu gì, nhóm phụ thuộc vào bạn ở đâu | 4 |
| **Nếu có 2h thêm** | 1 cải tiến cụ thể với lý do từ trace — không phải "làm tốt hơn chung chung" | 3 |

> **Điểm 0 cho mục nào nếu:** nội dung chỉ paraphrase slide, không có ví dụ cụ thể từ code/trace của nhóm, hoặc dưới 50 từ.

#### Rubric chi tiết — mục "1 quyết định kỹ thuật" (8 điểm)

| Mức | Mô tả | Điểm |
|-----|-------|------|
| **Xuất sắc** | Quyết định rõ ràng (VD: route_reason dùng keyword vs LLM classifier), có trade-off analysis, trace evidence | 7–8 |
| **Tốt** | Nêu quyết định và lý do, có liên kết với trace hoặc code thực tế | 5–6 |
| **Đạt** | Nêu quyết định nhưng lý do chung chung, không có evidence | 3–4 |
| **Yếu** | Chỉ mô tả code đã làm mà không giải thích được vì sao | 1–2 |
| **Không làm** | | 0 |

---

### 5. Code Contribution Evidence (10 điểm)

Chấm dựa trên **sự khớp giữa vai trò khai báo và bằng chứng thực tế trong repo**:

| Tiêu chí | Điểm |
|----------|------|
| Vai trò khai báo khớp với phần code có comment tên/initials hoặc commit message | 4 |
| Có thể giải thích quyết định kỹ thuật trong phần mình phụ trách | 4 |
| Không có mâu thuẫn giữa claim trong report và thực tế trong code/trace | 2 |

---

### ⚠️ Luật phạt nặng — Mất toàn bộ điểm cá nhân (0/40)

| Trường hợp | Mô tả | Hệ quả |
|-----------|-------|--------|
| **Report không khớp với code/trace** | Khai báo làm worker X nhưng trace không ghi output của worker X hoặc code không có evidence | **0/40 điểm cá nhân** |
| **Nhận công lao của người khác** | Khai báo implement phần mà thực tế thành viên khác làm | **0/40 điểm cá nhân** |
| **Report sao chép nhau** | Phân tích quyết định, lỗi, hoặc rút kinh nghiệm trùng lặp đáng kể | **0/40 của tất cả người liên quan** |
| **Không thể giải thích phần mình khai báo** | Khi được hỏi về routing logic hoặc worker contract, không giải thích được | **0/40 điểm cá nhân** |

---

## Tổng kết điểm

| Hạng mục | Tối đa | Người chấm |
|----------|--------|-----------|
| Sprint Deliverables | 20 | Giảng viên (chạy trực tiếp) |
| Group Documentation | 10 | Giảng viên |
| Grading Questions | 30 | Giảng viên (theo rubric) |
| **Tổng nhóm** | **60** | |
| Individual Report | 30 | Giảng viên |
| Code Contribution | 10 | Giảng viên |
| **Tổng cá nhân** | **40** | |
| **TỔNG** | **100** | |

---

## Điểm thưởng (Bonus — tối đa +5)

| Hành động | Thưởng |
|-----------|--------|
| Implement MCP server thật (không phải mock class) bằng `mcp` library hoặc HTTP server | +2 |
| Trace có `confidence` score thực tế (không hard-code) cho từng answer | +1 |
| Câu gq09 (câu khó nhất, 16 điểm) đạt Full marks + ghi đúng 2 workers trong trace | +2 |

---

## Tóm tắt hình phạt

| Vi phạm | Hình phạt |
|---------|-----------|
| Hallucinate trong grading questions | −50% điểm câu đó |
| Trace thiếu `route_reason` | −20% điểm câu đó |
| Report cá nhân không khớp với code/trace | **0/40 điểm cá nhân** |
| Nhận công lao của người khác | **0/40 điểm cá nhân** |
| Report sao chép nhau | **0/40 của tất cả người liên quan** |
| Commit code sau 18:00 | Commit đó không được tính |

---

## FAQ

**Nhóm chỉ có 2 người thì phân vai thế nào?**  
Người 1: Supervisor + Worker Owner (Sprint 1+2). Người 2: MCP + Trace + Docs Owner (Sprint 3+4). Báo cáo nhóm do người 2 nộp.

**Nếu pipeline crash khi chạy grading_questions?**  
Nộp log với các câu đã chạy được. Câu nào crash ghi `"answer": "PIPELINE_ERROR: [mô tả lỗi]"`. Không bị phạt thêm.

**Graph hay không cần LangGraph thật?**  
Không bắt buộc dùng LangGraph library. Có thể implement supervisor-worker bằng Python thuần với `if/else` routing. Quan trọng là trace phải ghi đủ fields.

**MCP phải thật hay mock được?**  
Mock class trong Python được tính full credit. Implement HTTP server thật được bonus +2.

**Trace file format là JSONL hay JSON?**  
File `artifacts/grading_run.jsonl` là JSONL (1 JSON object mỗi dòng). File trace trong `artifacts/traces/` có thể là `.json` hoặc `.jsonl`.

**Sau 18:00 còn commit được gì?**  
Chỉ `reports/group_report.md` và `reports/individual/[ten].md`. Mọi thay đổi khác sau 18:00 không được tính.

**Nếu không có Day 08 artifact, Sprint 1 bắt đầu thế nào?**  
Dùng `data/docs/` trong lab này. Build ChromaDB index nhỏ (5 docs) bằng script setup trong README. Không cần copy từ Day 08.

# Single Agent vs Multi-Agent Comparison — Lab Day 09

<<<<<<< HEAD
**Nhóm:** 4, E402
**Ngày:** 2026-04-14

Baseline Day 08 lấy từ `artifacts/day08_baseline/` (10 câu, chạy 2026-04-13).  
Day 09 LLM-Judge run bằng `score_grading.py` trên cùng 10 câu grading (2026-04-14, top_k=5).

---

## 1. Metrics Comparison

| Metric                   | Day 08 dense | Day 08 hybrid | Day 09 multi-agent | Ghi chú                                                                               |
|--------------------------|--------------|---------------|--------------------|---------------------------------------------------------------------------------------|
| **Faithfulness** (avg/5) | 4.60         | **5.00**      | **4.6**            | 1 judge error trên gq05 (contractor Admin Access — câu trả lời đúng nhưng judge nhầm) |
| **Relevance** (avg/5)    | 5.00         | 5.00          | **5.0**            | Bằng Day 08                                                                           |
| **Context Recall**       | 5.00         | 5.00          | **5.0**            | Bằng Day 08                                                                           |
| **Completeness** (avg/5) | 4.29         | 3.00          | **4.2**            | +1.2 vs hybrid; gần bằng dense — policy worker + MCP cải thiện multi-hop              |
| Avg confidence           | N/A          | N/A           | **0.73**           | Đo trực tiếp từ 10 grading questions                                                  |
| Avg latency              | ~2–3 s       | ~2–3 s        | **~4–6 s**         | +2–3× do Vertex AI embed                                                              |
| Abstain rate             | 0/10 (0%)    | 0/10 (0%)     | **1/10 (10%)**     | gq07 abstain đúng (không hallucinate số phạt)                                         |
| MCP usage rate           | N/A          | N/A           | **5/10 (50%)**     | policy/access/ticket câu trigger MCP                                                  |
| HITL rate                | N/A          | N/A           | **0/10 (0%)**      | Không có ERR-\d+ pattern trong grading set                                            |
| Routing visibility       | ✗            | ✗             | **✓ route_reason** | Mọi trace đều có lý do route                                                          |
| Test worker độc lập      | ✗            | ✗             | **✓**              | `python workers/retrieval.py`                                                         |

*Source: `artifacts/scorecard_day09_grading.md` (generated 2026-04-14)*

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

Ví dụ từ grading: **gq01** (SLA P1 version change), **gq04** (store credit %), **gq08** (HR leave policy), **gq09** (
password rotation)

| Nhận xét             | Day 08 hybrid            | Day 09 multi-agent                                  |
|----------------------|--------------------------|-----------------------------------------------------|
| Retrieval quality    | High (faithfulness 5.00) | High (same hybrid RRF)                              |
| Latency              | ~2–3 s                   | ~4–6 s (+2–3 s Vertex embed)                        |
| Routing overhead     | N/A                      | Minimal — `default route` hoặc `policy_tool_worker` |
| Scores (grading avg) | F=5.0, C=4.29 (dense)    | F=5.0, C=4.5 (gq04+gq08+gq09 avg)                   |

Grading kết quả:

- gq04: F=5 C=5 — store credit 110% retrieved and cited correctly
- gq08: F=5 C=4 — 3-day leave vs 3-day sick leave correctly disambiguated; minor nuance gap
- gq09: F=5 C=4 — 90-day / 7-day / SSO portal all correct; missing full URL

**Kết luận:** Với câu đơn giản, multi-agent không cải thiện chất lượng trả lời (retrieval và synthesis giống nhau),
nhưng tốn thêm ~2–3 s latency do Vertex AI embedding. Trade-off chấp nhận được vì câu đơn giản không phải mục tiêu tối
ưu hoá.

### 2.2 Câu hỏi multi-hop (cross-document)

Ví dụ từ grading: **gq05** (contractor Admin Access Level 4), **gq06** (P1 2am emergency + 24h temp access)

| Nhận xét                  | Day 08 hybrid             | Day 09 multi-agent                                                 |
|---------------------------|---------------------------|--------------------------------------------------------------------|
| Coverage                  | 1 retrieval pass duy nhất | policy_tool + retrieval + MCP tools                                |
| Routing visible?          | ✗                         | ✓ `route_reason` ghi rõ keyword triggered                          |
| MCP context               | Không có                  | `check_access_permission` + `get_ticket_info` bổ sung live context |
| Completeness (gq05, gq06) | Phụ thuộc chunk overlap   | Policy worker + MCP → C=5 trên cả hai                              |

Grading kết quả:

- gq06: F=5 C=5 — 4 key facts đều đúng (IT Admin, Tech Lead, 24h, Security Audit log); MCP context được synthesis cite
  trực tiếp
- gq05: F=**1** C=5 — nội dung đúng hoàn toàn (IT Manager + CISO, 5 ngày, training) nhưng judge calibration error (judge
  nhầm scope clause)

**Kết luận:** Day 09 vượt trội trên multi-hop — policy worker tách exception detection; synthesis context bao gồm cả KB
chunks và MCP tool outputs để cite live data. Day 08 hybrid phụ thuộc hoàn toàn vào retrieval chunk quality — nếu chunk
không chứa đủ condition (Level 4 vs Level 3) thì synthesis có thể lẫn lộn.

### 2.3 Câu hỏi cần abstain

Ví dụ từ grading: **gq07** (SLA P1 penalty — không có trong docs)

| Nhận xét       | Day 08 hybrid             | Day 09 multi-agent                            |
|----------------|---------------------------|-----------------------------------------------|
| gq07 answer    | Không đo được (eval khác) | "Không đủ thông tin trong tài liệu nội bộ."   |
| Confidence     | N/A                       | **0.30**                                      |
| HITL triggered | N/A                       | ✗ (không phải ERR-\d+ pattern)                |
| Hallucination  | Không rõ                  | Không — pipeline từ chối bịa số phạt          |
| Faithfulness   | N/A                       | **5** (abstain-override: expected_sources=[]) |

**Kết luận:** gq07 là hallucination bait điển hình — không có tài liệu nào nêu mức phạt SLA vi phạm. Day 09 abstain đúng
với confidence=0.30. HITL không trigger (gq07 không phải ERR-\d+ pattern — đây là "unknown information" không phải "
unknown error code"). `score_grading.py` xử lý judge calibration bằng abstain-override: khi `expected_sources=[]` và
answer chứa "Không đủ thông tin", F và R được override lên 5/5.

---

## 3. Debuggability Analysis

### Day 08 — Debug workflow

```
Answer sai → phải đọc toàn bộ rag_answer.py
→ tìm lỗi: indexing? chunking? retrieval? prompt? không rõ
→ không có trace → không biết chunk nào đã retrieve
→ Ước tính: 15–20 phút để tìm nguyên nhân
```

### Day 09 — Debug workflow

```
Answer sai → mở artifacts/traces/{run_id}.json
→ đọc route_reason: biết ngay route đúng chưa
→ đọc retrieved_chunks: biết retrieval trả về gì
→ đọc mcp_tools_used: biết MCP output
→ đọc worker_io_logs: biết từng worker nhận và trả gì
→ Nếu route sai: sửa supervisor keyword list
→ Nếu retrieval sai: uv run python workers/retrieval.py
→ Nếu synthesis sai: uv run python workers/synthesis.py
→ Ước tính: 3–5 phút để tìm nguyên nhân
```

**Ví dụ debug thực tế trong lab:**  
Trong quá trình implement Sprint 2, synthesis trả về confidence 0.02 thay vì 0.7+ cho câu retrieval bình thường. Nguyên
nhân: RRF scores (~0.008) nhỏ hơn 0.1, nhưng max normalisation logic có bug (`max_score=0` branch). Phát hiện bằng cách
đọc `worker_io_logs[synthesis_worker].output.confidence` trong trace → sửa `_estimate_confidence()` trong 5 phút. Không
cần trace mà tìm bug này trong monolith sẽ mất rất lâu.

---

## 4. Extensibility Analysis

| Scenario                                  | Day 08                            | Day 09                                                                       |
|-------------------------------------------|-----------------------------------|------------------------------------------------------------------------------|
| Thêm 1 tool mới (e.g., HR API)            | Phải sửa prompt + retrieval       | Thêm 1 tool vào `mcp_server.py` + 1 trigger rule trong `policy_tool.py`      |
| Thêm 1 domain mới (e.g., Finance)         | Phải re-index và re-tune prompt   | Thêm 1 worker `finance_worker.py` + route rule trong supervisor              |
| Thay đổi retrieval strategy               | Sửa trực tiếp trong pipeline code | Sửa `retrieve_hybrid()` trong `workers/retrieval.py` độc lập                 |
| A/B test retrieval (dense vs hybrid)      | Phải clone toàn pipeline          | Thay `retrieve_hybrid` → `retrieve_dense` trong `run()` của retrieval_worker |
| Thêm LLM intent classifier cho supervisor | Cần refactor lớn                  | Chỉ sửa `supervisor_node()` trong `graph.py`                                 |

---

## 5. Cost & Latency Trade-off

| Scenario                      | Day 08 LLM calls | Day 09 LLM calls                 | Day 09 latency |
|-------------------------------|------------------|----------------------------------|----------------|
| Simple query (retrieval only) | 1 (synthesis)    | 1 (synthesis)                    | ~5–7 s         |
| Policy query (no MCP)         | 1 (synthesis)    | 1 (synthesis)                    | ~5–7 s         |
| Policy query + MCP tools      | 1 (synthesis)    | 1 (synthesis) + 3 in-process MCP | ~7–9 s         |
| Human review + retrieval      | 1 (synthesis)    | 1 (synthesis)                    | ~4–5 s         |

**Ghi chú về latency:**  
Day 09 chậm hơn Day 08 chủ yếu do Vertex AI embedding (~2–3 s/query, cả indexing và retrieval time) chứ không phải do
multi-agent overhead. Số lượng LLM calls vẫn là 1 per run — synthesis worker. MCP tools là in-process Python function
calls, latency không đáng kể (<10 ms).

**Cost-benefit:**  
Thêm ~4 s latency để đổi lấy routing visibility, MCP context, và debuggable traces là trade-off hợp lý cho enterprise
helpdesk (không cần real-time sub-second response). Nếu cần giảm latency, thay Vertex AI → OpenAI
`text-embedding-3-small` (faster, lower cost).

---

## 6. Kết luận

**Multi-agent tốt hơn single agent ở:**

1. **Debuggability** — trace có `route_reason`, `worker_io_logs`, `mcp_tools_used` → tìm bug nhanh hơn 3–5×
2. **Multi-hop completeness** — policy worker tách exception detection; MCP tools cung cấp context live (ticket status,
   access rules) mà pure retrieval không có
3. **Extensibility** — thêm tool hoặc domain không cần sửa core pipeline; chỉ thêm worker hoặc MCP tool

**Multi-agent kém hơn hoặc không khác biệt:**

1. **Latency** — Day 09 chậm hơn ~2–3× do Vertex AI embedding (không phải do multi-agent pattern)
2. **Simple queries** — câu đơn giản (SLA, HR policy) không hưởng lợi từ routing; chất lượng trả lời giống nhau

**Khi nào KHÔNG nên dùng multi-agent:**  
Khi corpus đơn giản, câu hỏi không có multi-hop, latency là yêu cầu quan trọng, và đội ngũ nhỏ không có resource để
maintain nhiều worker. Single-agent RAG đơn giản hơn nhiều và dễ onboard hơn.

**Nếu tiếp tục phát triển:**

- Thay keyword routing trong supervisor bằng LLM intent classifier (giải quyết false positive "hoàn tiền" → policy_tool
  cho câu retrieval đơn giản)
- Implement real HTTP MCP server với FastAPI để test network boundary
- Thêm LLM-as-Judge tích hợp vào `eval_trace.py` để tự động tính faithfulness/completeness trên mọi run, không chỉ Day
  08 baseline
=======
**Nhóm:** 04 
**Ngày:** 2026-04-14

## 0) Quy tắc điền số liệu

- Ưu tiên số liệu thật từ trace/report.
- Nếu chưa có Day 08 baseline thật, ghi `N/A (chưa có artifact)` và nêu kế hoạch bổ sung.
- Không điền số "đoán"; rubric chấm tính nhất quán giữa report và artifact.

## 1) Nguồn dữ liệu dùng để so sánh

- Day 09:
  - `python eval_trace.py --analyze`
  - `python eval_trace.py --compare`
  - `artifacts/traces/*.json`
- Day 08:
  - `eval.py` hoặc file baseline do nhóm lưu
  - Hiện tại: `N/A (chưa có artifact Day08 trong repo này)`

## 2) Metrics Comparison (bảng chính)

| Metric | Day 08 (Single) | Day 09 (Multi) | Delta | Trạng thái dữ liệu | Ghi chú |
|---|---:|---:|---:|---|---|
| Avg confidence | N/A | 0.739 | N/A | Day08: Placeholder / Day09: Real | từ `artifacts/eval_report.json` |
| Avg latency (ms) | N/A | 3494 | N/A | Day08: Placeholder / Day09: Real | |
| Abstain rate (%) | N/A | Thấp | N/A | Day08: Placeholder / Day09: Estimated | phần lớn câu đã có evidence |
| Multi-hop accuracy | N/A | Trung bình-khá (ước lượng) | N/A | Day08: Placeholder / Day09: Estimated | q15 có đủ 2 nguồn |
| Routing visibility | Không có | Có `route_reason` | N/A | Real | |
| MCP usage rate (%) | N/A | 33% (5/15) | N/A | Real | lấy từ `analyze_traces()` |
| HITL rate (%) | N/A | 6% (1/15) | N/A | Real | |
| Debug time cho 1 lỗi (phút) | N/A | 5-10 | N/A | Estimated | có route_reason + worker_io_logs |

> Ghi chú quan trọng: trong `eval_trace.py`, baseline Day 08 mặc định còn TODO nếu không truyền file baseline thật.

## 3) Phân tích theo nhóm câu hỏi

### 3.1 Simple retrieval

| Tiêu chí | Day 08 | Day 09 | Nhận xét |
|---|---|---|---|
| Accuracy | N/A | Khá | Retrieval đã có chunks + sources rõ |
| Latency | N/A | ~3.5s trung bình | Đã giảm sau khi đồng bộ embedding |
| Độ ổn định | N/A | Tốt | 15/15 câu chạy thành công |

### 3.2 Multi-hop / cross-policy (đặc biệt gq09)

| Tiêu chí | Day 08 | Day 09 | Nhận xét |
|---|---|---|---|
| Trả đủ 2 ý chính | N/A | Trung bình-khá | q15 đã trả được cả access + SLA từ 2 source |
| Có evidence trace route/worker | Không | Có | |
| Khả năng debug khi thiếu 1 ý | N/A | Tốt | Có `route_reason`, `workers_called`, `worker_io_logs` |

### 3.3 Câu cần abstain (đặc biệt gq07)

| Tiêu chí | Day 08 | Day 09 | Nhận xét |
|---|---|---|---|
| Tỉ lệ abstain đúng | N/A | Vừa phải | abstain xuất hiện khi evidence yếu |
| Hallucination cases | N/A | Thấp | câu trả lời có citation rõ hơn |
| Mức phạt dự kiến theo rubric | N/A | Giảm rủi ro so với lần chạy trước | |

## 4) Debuggability và khả năng vận hành

### Flow debug Day 08

```text
Answer sai -> đọc pipeline chung -> khó định vị retrieval/prompt/policy sai
```

### Flow debug Day 09

```text
Answer sai -> xem supervisor_route + route_reason + workers_called
-> route sai: sửa supervisor
-> route đúng nhưng output sai: test worker tương ứng độc lập
```

**Case debug thực tế của nhóm:**  
Trace `run_20260414_165615.json` cho thấy retrieval đã trả 3 chunks với source chuẩn, xác nhận fix đồng bộ embedding đã có hiệu lực.

## 5) Kết luận có thể chấm điểm

### Multi-agent tốt hơn ở

1. Quan sát pipeline theo từng worker rõ ràng, debug nhanh hơn.
2. Tích hợp MCP độc lập, không phải chỉnh prompt toàn hệ.

### Multi-agent chưa tốt hơn ở

1. Chưa có baseline Day08 thật nên chưa kết luận được delta tuyệt đối.

### Rủi ro cần ghi trung thực trong report

- Day08 baseline chưa có artifact thật trong repo nên chưa tính được delta.
- Một số metric comparison có thể còn placeholder nếu thiếu baseline Day 08.
- Chưa có `grading_run.jsonl` nên chưa chốt score raw/96.

### Kế hoạch cải thiện vòng sau

1. Chạy `eval_trace.py --grading` để có kết quả chấm thật.
2. Bổ sung artifact Day08 để tính delta latency/accuracy đầy đủ.
>>>>>>> NhatVi

# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Đỗ Minh Phúc
**Mã học viên:** 2A202600039
**Vai trò trong nhóm:** Worker Owner (Synthesis Worker) + Integrator
**Ngày nộp:** 14/04/2026

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Em phụ trách chính `workers/synthesis.py` và đảm nhiệm vai trò integrator xuyên suốt cả 3 worker của nhóm.

**Ownership chính — Synthesis Worker:** em viết lại worker tổng hợp câu trả lời (commit `c891ef7`) với các thành phần: citation format `[n]` khớp `contracts/worker_contracts.yaml`, cơ chế early-abstain khi không có chunks (bỏ qua LLM để chống hallucinate), HITL auto-trigger khi `confidence < 0.4`, confidence heuristic có `citation bonus + exception penalty`, và 2 test case độc lập (no-chunks abstain + multi-chunk citation).

**Ownership phụ — Integration & End-to-end:** commit `3040d12` chỉnh sửa theo phản hồi Copilot review #3 cho cả 3 worker (synthesis, policy_tool, retrieval) để đồng bộ với contract; commit `5b92dd1` refactor `graph.py` (−78 dòng), build lại ChromaDB index và chạy 15 test questions sinh trace đầy đủ; commit `5876bf8` + `43cfd5d` chạy và nộp `artifacts/grading_run.jsonl` cho 10 câu grading.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** dùng **sentinel string (`LLM_ERROR_SENTINEL = "__LLM_CALL_FAILED__"`) cho lỗi LLM** thay vì raise exception hoặc trả chuỗi rỗng, sau đó map sentinel thành abstain + `confidence=0.1` + cờ `llm_error` trong worker_io_log.

**Các phương án đã cân nhắc:**

| Phương án                     | Ưu điểm                                                       | Nhược điểm                                             |
| ----------------------------- | ------------------------------------------------------------- | ------------------------------------------------------ |
| A.`raise` exception           | Fail-fast rõ ràng                                             | Vỡ pipeline giữa batch eval → mất trace các câu khác   |
| B. Trả `""` khi lỗi           | Pipeline tiếp tục                                             | Silent: không phân biệt "LLM không biết" vs "LLM chết" |
| **C. Sentinel + map abstain** | Pipeline tiếp tục, phân biệt được lỗi LLM vs abstain nội dung | Thêm 1 hằng số + vài dòng caller                       |

**Lý do chọn C:** trong batch eval 15 câu, nếu 1 câu làm crash LLM (rate limit, key hết hạn) thì toàn bộ trace còn lại mất. Sentinel giữ pipeline chạy, đồng thời trong trace có thể truy ngược: `worker_io_log.error` + `confidence=0.1` + cờ `llm_error=True` đủ để phân biệt lỗi hạ tầng và abstain "thật".

**Bằng chứng:** commit `e39df97` — hàm `_call_llm` trả sentinel; `synthesize()` check sentinel trước `_is_abstain()` thường; `run()` reset `hitl_triggered=False` ở đầu để không rò trạng thái giữa các câu. Trong giai đoạn `.env` chưa load được, mọi câu abstain với confidence 0.1 nhưng toàn bộ 15 trace vẫn ghi đầy đủ — không trace nào bị mất do exception.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** synthesis worker có thể trả confidence cao (~0.65) cho câu trả lời **không có citation** `[1]`, `[2]` dù có chunks trong context. Người đọc tưởng câu trả lời grounded nhưng thực ra không ràng buộc được đoạn nào từ tài liệu — đây là dạng "grounded ảo" cực nguy hiểm với rubric grading.

**Symptom:** khi LLM "lười" không chèn `[n]`, `_estimate_confidence` chỉ trừ nhẹ mà không set `hitl_triggered`. Trong vài trace sơ khai, có answer chứa fact đúng nhưng không citation nào — grader không thể verify nguồn.

**Root cause:** logic HITL trigger ban đầu chỉ dựa trên ngưỡng `confidence < 0.4`. Khi answer mất citation, confidence bị phạt xuống ~0.55–0.65 nhưng vẫn trên ngưỡng nên HITL không kích hoạt. Lỗ hổng: hai tiêu chí "low confidence" và "missing citation" bị gộp làm một, mất tín hiệu riêng biệt.

**Cách sửa (commit `3040d12`, synthesis.py):** nếu `chunks` tồn tại nhưng `_has_citation(answer)` trả `False` → **force `hitl_triggered=True`** bất kể giá trị confidence, đồng thời docstring `synthesize()` ghi rõ intent. Thêm `state.setdefault("hitl_triggered", False)` ở đầu `run()` để cờ HITL không bị rò từ worker chạy trước.

**Before/After:** trước fix, có trace `gq02` trả conf 0.74 không citation nhưng `hitl_triggered=False` → sau fix, cùng loại input bật HITL đúng, khớp yêu cầu citation bắt buộc trong `contracts/worker_contracts.yaml` (synthesis worker: citation required when chunks present).

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Điểm mạnh:** em làm tốt phần cross-integration — không chỉ sở hữu 1 worker mà còn áp Copilot review đồng loạt cho cả 3 worker để contract đồng bộ (`3040d12`). Vai trò integrator giúp graph chạy end-to-end ổn định ngay từ lần merge đầu.

**Điểm yếu:** em dành quá nhiều thời gian cho vòng lặp Copilot review synthesis (2 commit `c891ef7` → `e39df97` trong 30 phút) — nếu gộp review từ đầu, Sprint 2 giao sớm hơn 30 phút, các thành viên downstream có thêm thời gian test. Confidence vẫn là heuristic chứ chưa calibrate bằng LLM-as-judge, khiến `q11`, `q12` bị chấm oan conf 0.30 dù answer đúng nội dung.

**Nhóm phụ thuộc vào tôi ở đâu:** synthesis là node cuối — mọi answer của nhóm đều đi qua worker này. Nếu sai contract citation hoặc abstain, cả 10 câu grading mất điểm.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Em sẽ thay `_estimate_confidence` heuristic bằng **LLM-as-judge confidence** — prompt riêng yêu cầu GPT-4o-mini chấm (thang 0–1) mức độ câu trả lời grounded vào chunks. Bằng chứng lý do: trong trace test, câu `q11` và `q12` có answer đúng nhưng heuristic phạt conf xuống 0.30 do detect exceptions, kích hoạt HITL sai. LLM-as-judge đọc cả answer + chunks và đánh giá actual grounding, ước tính giảm `hitl_rate` từ 20% xuống ~10% và không đánh giá oan câu đúng.

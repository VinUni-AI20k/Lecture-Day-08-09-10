# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Tiến Dũng 
**Vai trò trong nhóm:** Worker Owner
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

> **Lưu ý quan trọng:**
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm
> - Deadline: Được commit **sau 18:00** (xem SCORING.md)
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`)

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong Lab Day 09, tôi đảm nhận vai trò Worker Owner, implement hai worker cốt lõi của hệ thống Multi-Agent Pipeline.

**Module/file tôi chịu trách nhiệm:**
- File chính 1: `workers/policy_tool.py`
- File chính 2: `workers/synthesis.py`
- Functions tôi implement:
  - `_call_llm()`, `_extract_date_from_task()`, `_is_before_policy_v4()`, `_llm_analyze_policy()`, `analyze_policy()` - trong `policy_tool.py`
  - `_call_llm()` (sửa lại), `_estimate_confidence()` (nâng cấp LLM-as-Judge), `run()` (thêm HITL trigger) - trong `synthesis.py`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

`policy_tool_worker` và `synthesis_worker` có vai trò trong pipeline: Supervisor route câu hỏi đến đúng worker, `retrieval_worker` cung cấp chunks, rồi hai worker xử lý phân tích policy và tổng hợp câu trả lời. Nếu hai worker này không trả đúng format AgentState, toàn bộ trace sẽ thiếu các field bắt buộc như `policy_result`, `final_answer`, `confidence`.

**Bằng chứng (commit hash):**

Commit `650bc04` - `TranTienDung implement policy_tool + synthesis workers with LLM analysis` (14/04/2026)

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Thiết kế `analyze_policy()` theo kiến trúc 2 lớp - Rule-based + LLM thay vì chọn một trong hai.
Khi implement `workers/policy_tool.py`, tôi đứng trước lựa chọn:
- **Option A:** Chỉ dùng rule-based keyword matching - đơn giản, không cần API, nhưng dễ bỏ sót các case phức tạp (ví dụ: "Flash Sale nhưng lỗi nhà sản xuất" là exception-of-exception).
- **Option B:** Chỉ gọi LLM để phân tích - linh hoạt hơn, nhưng tốn token và dễ bị LLM hallucinate thêm rule không có trong tài liệu.
- **Option C (tôi chọn):** Kết hợp - rule-based chạy trước làm fast-path cho các exception rõ ràng, LLM chạy sau để detect edge cases, kết quả được merge và dedup theo `type`.

Lý do chính: theo `worker_contracts.yaml`, worker không được "tự bịa policy rules không có trong tài liệu". Rule-based đảm bảo điều này cho 3 exception cứng (Flash Sale, digital product, activated), còn LLM chỉ được phép bổ sung exception nếu context từ KB hỗ trợ.

**Trade-off đã chấp nhận:** Mỗi lần gọi `policy_tool_worker` sẽ thực hiện 1 LLM call thêm, tăng latency khoảng 500–800ms. Nhưng đây là chấp nhận được vì policy questions là high-risk, cần độ chính xác cao hơn SLA questions.

**Bằng chứng từ code:**

```python
# workers/policy_tool.py — analyze_policy()

# ── Layer 1: Rule-based exception detection ──────────────────────────
exceptions_found = []
if "flash sale" in task_lower or "flash sale" in context_text:
    is_manufacturer_defect = any(kw in task_lower for kw in [
        "lỗi nhà sản xuất", "lỗi sản xuất", "manufacturer", "defect"
    ])
    if is_manufacturer_defect:
        exceptions_found.append({"type": "flash_sale_manufacturer_defect", ...})
    else:
        exceptions_found.append({"type": "flash_sale_exception", ...})

# ── Layer 2: LLM-based deep analysis ──────────────────────────────────
llm_result = _llm_analyze_policy(task, chunks)

# Merge: dedup by type, LLM không thể override rule-based
existing_types = {ex["type"] for ex in exceptions_found}
for llm_ex in llm_result.get("llm_exceptions", []):
    if llm_ex.get("type") not in existing_types:
        exceptions_found.append(llm_ex)
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `synthesis_worker` trả về `[SYNTHESIS ERROR]` và `confidence: 0.0` dù `OPENAI_API_KEY` đã có trong `.env`.

**Symptom:**

Khi chạy `python workers/synthesis.py` standalone, output luôn là:
```
Answer:
[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env.
Confidence: 0.0
```

**Root cause:**

File `synthesis.py` gốc từ upstream thiếu hai vấn đề:
1. **Thiếu `load_dotenv()`** - khi chạy standalone, file không tự load `.env`, nên `os.getenv("OPENAI_API_KEY")` trả về `None`.
2. **`_call_llm()` không kiểm tra key trước khi gọi** - hàm gọi `OpenAI(api_key=None)` và bắt exception bằng `except Exception: pass` (silent), không log lỗi, dẫn đến fallback ngay sang Gemini rồi cũng fail im lặng.

**Cách sửa:**

```python
# Thêm ở đầu file
from dotenv import load_dotenv
load_dotenv()

# Sửa _call_llm(): check key trước, log lỗi rõ ràng
def _call_llm(messages: list) -> str:
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:  # Chỉ gọi nếu có key
        try:
            ...
        except Exception as e:
            print(f"[synthesis] OpenAI error: {e}")  # Verbose logging
    ...
```

**Bằng chứng trước/sau:**

*Trước khi sửa:*
```
Answer: [SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env.
Confidence: 0.0
```

*Sau khi sửa:*
```
Answer: SLA cho ticket P1 là phản hồi ban đầu trong 15 phút kể từ khi ticket được tạo,
        xử lý và khắc phục trong 4 giờ. [sla_p1_2026.txt]
Sources: ['sla_p1_2026.txt']
Confidence: 0.95
HITL triggered: False
```

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Tôi thiết kế được hệ thống phân tích policy có tính phòng thủ cao: rule-based làm guard đầu tiên để tránh LLM hallucinate policy, LLM chỉ bổ sung exception nếu context từ KB thực sự hỗ trợ. Ngoài ra, phần `_estimate_confidence()` với LLM-as-Judge (3 tiêu chí: faithfulness, completeness, anti-hallucination) giúp confidence score có ý nghĩa thực sự, thay vì chỉ là trung bình cộng của chunk scores.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Khi `git stash` + `git pull`, toàn bộ code của tôi bị overwrite bởi bản cũ từ remote và tôi không phát hiện ngay - phải mất thêm thời gian để rewrite lại. Tôi chưa có thói quen commit trước khi pull khi làm việc nhóm.

**Nhóm phụ thuộc vào tôi ở đâu?**

Nếu `synthesis_worker` chưa xong, toàn bộ pipeline không có `final_answer` - UI hiển thị trống và trace file thiếu field bắt buộc. Phần `confidence` và `hitl_triggered` trong AgentState cũng do tôi set ảnh hưởng đến logic HITL của Supervisor.

**Phần tôi phụ thuộc vào thành viên khác:**

Tôi cần `retrieval_worker` của team cung cấp `retrieved_chunks` đúng format `{text, source, score}` trước khi `policy_tool` và `synthesis` có thể chạy. Nếu chunks thiếu field `score`, hàm `_estimate_confidence()` fallback về heuristic với default `0.5`.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ cải thiện **temporal scoping** trong `policy_tool_worker`. Hiện tại, hàm `_is_before_policy_v4()` chỉ detect ngày cụ thể trong câu hỏi (dạng DD/MM/YYYY) nhưng chưa xử lý được các câu như _"đơn hàng tháng trước"_ hay _"đặt hàng hồi tháng 1"_. Trace của một số test case cho thấy `policy_version_note` trả về rỗng với các câu hỏi dùng ngôn ngữ tự nhiên về thời gian thay vì ngày cụ thể. Tôi sẽ bổ sung thêm một bước NER date extraction bằng LLM để bắt được các biểu đạt thời gian mơ hồ này.

---

*Lưu file này với tên: `reports/individual/Tran_Tien_Dung.md`*

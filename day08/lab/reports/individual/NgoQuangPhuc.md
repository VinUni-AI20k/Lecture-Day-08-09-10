# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Ngô Quang Phúc

**Vai trò trong nhóm:** Evaluation Specialist

**Ngày nộp:** 2026-04-13

**Độ dài yêu cầu:** 500–800 từ

---

## 1. Đóng góp cụ thể

Tôi phụ trách toàn bộ Sprint 4 — xây dựng `eval.py` từ đầu. Cụ thể:

**Bốn hàm scoring (LLM-as-Judge):**
- `score_faithfulness(answer, chunks_used)`: Gửi retrieved context + answer lên LLM judge, hỏi "mọi claim trong answer có được support bởi context không?", nhận JSON `{"score": 1-5, "reason": "..."}`. Kết quả baseline: trung bình **4.50/5**.
- `score_answer_relevance(query, answer)`: Gửi câu hỏi + answer, chấm xem có trả lời đúng trọng tâm không. Baseline: **4.20/5** — thấp do q09 và q10 bị điểm 1 (model trả lời "Tôi không biết" hoặc không mention quy trình mặc định).
- `score_context_recall(chunks_used, expected_sources)`: Kiểm tra partial match tên file giữa retrieved sources và expected sources. Trả về `None` (không phải 0) khi `expected_sources = []` để tránh làm sai average — áp dụng cho q09. Baseline: **5.00/5** trên 9 câu có expected source.
- `score_completeness(query, answer, expected_answer)`: So sánh answer với reference answer qua LLM judge. Baseline: **3.80/5** — metric thấp nhất, phản ánh model hay bỏ sót chi tiết.

**Hàm điều phối:**
- `run_scorecard(config)`: Vòng lặp 10 câu, gọi `rag_answer()`, gọi 4 hàm scoring, in bảng kết quả và tính average (bỏ qua `None`).
- `compare_ab(baseline_results, variant_results)`: In bảng delta theo metric và per-question, export CSV.
- `generate_scorecard_summary(results, label)`: Xuất `results/scorecard_baseline.md`.
- `generate_grading_log()`: Chạy với `grading_questions.json`, xuất `logs/grading_run.json` theo format chuẩn nộp bài.

---

## 2. Phân tích 1 câu trong scorecard

**Câu q07:** *"Approval Matrix để cấp quyền hệ thống là tài liệu nào?"*

**Kết quả scorecard baseline:**

| Metric | Điểm |
|--------|------|
| Faithfulness | 5/5 |
| Answer Relevance | 5/5 |
| Context Recall | 5/5 |
| Completeness | **2/5** |

**Answer thực tế của pipeline:**
> *"Approval Matrix để cấp quyền hệ thống là tài liệu có tên 'Approval Matrix for System Access' [1]."*

**Expected answer:**
> *"Tài liệu 'Approval Matrix for System Access' hiện tại có tên mới là 'Access Control SOP' (access-control-sop.md)."*

**Trace failure mode:**

Câu này là alias query — người dùng dùng tên cũ "Approval Matrix", trong khi tài liệu thực tế đã đổi tên thành "Access Control SOP". Dòng 7 trong `access_control_sop.txt` ghi rõ: *"Tài liệu này trước đây có tên 'Approval Matrix for System Access'."*

- **Tầng Retrieval — PASS:** `Context Recall = 5/5`. Retriever dense đã tìm đúng file `it/access-control-sop.md` dù query dùng tên cũ. Dense embedding đủ semantic để match "Approval Matrix" với "Access Control SOP".
- **Tầng Generation — FAIL:** `Completeness = 2/5`. Model trích được chunk có chứa tên cũ nhưng **chỉ echo lại tên cũ** ("Approval Matrix for System Access") mà không kết nối sang tên mới. Câu trả lời đúng theo nghĩa literal nhưng thiếu thông tin cốt lõi: tên hiện tại của tài liệu là gì.

**Root cause:** Prompt template trong `rag_answer.py` không hướng dẫn model xử lý trường hợp tài liệu có alias. Model chỉ được yêu cầu "trả lời dựa trên context" — nên nó lấy câu đầu tiên trong chunk có từ "Approval Matrix" mà không đọc tiếp để thấy tên mới. Đây là lỗi **generation**, không phải indexing hay retrieval.

**Fix cụ thể:** Thêm instruction vào system prompt: *"Nếu tài liệu đề cập tên cũ/alias, hãy nêu rõ cả tên hiện tại lẫn tên cũ trong câu trả lời."*

---

## 3. Rút kinh nghiệm

**Điều ngạc nhiên:** `Context Recall = 5.00/5` cho tất cả 9 câu có expected source — kể cả q07 (alias query) và q10 (VIP refund không có trong docs). Trước khi chạy eval, tôi dự đoán q07 sẽ fail retrieval vì query dùng tên cũ, nhưng dense embedding đủ mạnh để match semantic. Điều này chứng minh bottleneck thực sự của pipeline nằm ở **generation**, không phải retrieval — một kết luận khác hẳn với giả thuyết ban đầu.

**Khó khăn kỹ thuật thực tế:** Parse JSON từ LLM judge không ổn định. Judge đôi khi trả về JSON bọc trong markdown code block (` ```json ... ``` `) hoặc kèm text giải thích phía trước. Giải pháp tôi dùng: `raw.find("{")` và `raw.rfind("}")` để extract substring JSON trước khi `json.loads()`. Nếu vẫn fail thì fallback về `{"score": None, "reason": "Parse lỗi"}` để không crash toàn bộ scorecard — đây không phải pattern tôi đọc từ slide mà là fix thực tế khi chạy thấy lỗi.

**Bài học:** Khi dùng LLM làm judge, prompt cần thang điểm mô tả từng mức cụ thể và yêu cầu output JSON có schema rõ ràng. Prompt mơ hồ dẫn đến score không nhất quán giữa các lần gọi cùng input.

---

## 4. Đề xuất cải tiến

**Cải tiến 1 — Fix generation cho alias queries (evidence: q07 Completeness = 2/5):**
Thêm vào system prompt của `rag_answer.py`: *"Nếu context đề cập tên cũ hoặc alias của tài liệu, hãy nêu rõ tên hiện tại."* Chi phí thay đổi thấp (1 dòng prompt), tác động trực tiếp lên completeness của q07 và các câu alias tương tự.

**Cải tiến 2 — Hướng dẫn model fallback khi thiếu context đặc biệt (evidence: q10 Relevance = 1/5):**
Q10 hỏi về quy trình VIP refund — không có trong docs. Model trả lời đúng "không có thông tin đặc biệt" nhưng không mention quy trình tiêu chuẩn vẫn áp dụng (3–5 ngày), khiến Relevance = 1/5. Fix: thêm instruction *"Nếu không có quy trình đặc biệt, hãy nêu rõ quy trình mặc định đang áp dụng."* Cải tiến này bám sát lỗi thật từ scorecard, không phải "cải thiện chung chung".

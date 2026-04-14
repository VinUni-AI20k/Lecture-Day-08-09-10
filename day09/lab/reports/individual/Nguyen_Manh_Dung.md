# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Mạnh Dũng
**Vai trò trong nhóm:** Synthesis Worker
**Ngày nộp:** 2026-04-14
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong dự án Lab Day 09, tôi đảm nhận vai trò **Synthesis Worker**, chịu trách nhiệm chính trong việc tổng hợp câu trả lời cuối cùng từ các dữ liệu thô do các thành viên khác cung cấp.

**Module/file tôi chịu trách nhiệm:**
- File chính: `day09/lab/workers/synthesis.py`
- Functions tôi implement: `synthesize()`, `run()`, `_build_context()`, `_estimate_confidence()`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Module của tôi đóng vai trò là "điểm cuối" trong pipeline xử lý của Worker. Tôi tiếp nhận danh sách `retrieved_chunks` từ Tuấn (Retrieval Worker) và `policy_result` từ Hải (Policy Tool Worker). Sau khi xử lý, tôi cung cấp `final_answer`, danh sách `sources`, điểm `confidence` và cờ `hitl_flag` cho Supervisor (Quang) để hoàn tất yêu cầu của người dùng. Dữ liệu tôi sinh ra cũng là đầu vào quan trọng cho Long (Trace & Eval) để đánh giá chất lượng toàn bộ hệ thống.

**Bằng chứng:**
File `day09/lab/workers/synthesis.py` chứa toàn bộ logic xử lý và prompt cho phần Synthesis và LLM-as-Judge.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi đã quyết định triển khai một cơ chế **LLM-as-Judge** (hàm `_estimate_confidence`) để tự động đánh giá mức độ tin cậy của câu trả lời, thay vì sử dụng các phương pháp tính điểm tĩnh hoặc dựa trên độ tương đồng vector (Cosine Similarity) của các chunks đầu vào.

**Lý do:** 
Độ tương đồng vector chỉ phản ánh việc tài liệu có "vẻ ngoài" liên quan đến câu hỏi hay không, nhưng không đảm bảo rằng LLM đã tổng hợp thông tin đó một cách chính xác mà không bị ảo giác (hallucination). Bằng cách sử dụng một prompt `JUDGE_PROMPT` chuyên biệt để yêu cầu LLM đóng vai trò QA Judge, tôi có thể đánh giá trực tiếp tính Groundedness (có căn cứ) và Completeness (tính đầy đủ) của câu trả lời dựa trên context thực tế được cung cấp.

**Trade-off đã chấp nhận:**
Quyết định này đánh đổi về mặt hiệu năng (latency tăng thêm khoảng 1-1.5 giây cho mỗi query) và chi phí API token (phải gọi LLM thêm một lần nữa). Tuy nhiên, đối với một hệ thống hỗ trợ IT Helpdesk và Policy nội bộ, độ chính xác và khả năng kiểm soát lỗi (qua cờ HITL) quan trọng hơn tốc độ phản hồi tức thời.

**Bằng chứng từ trace/code:**
```python
def _estimate_confidence(task: str, context: str, answer: str) -> float:
    # ... (code gọi LLM với JUDGE_PROMPT)
    score_str = _call_llm(judge_messages, temperature=0)
    # ... (extract score từ chuỗi trả về)
```
Trong trace, kết quả trả về luôn kèm theo `confidence` score (ví dụ: 0.85) giúp hệ thống quyết định có cần con người can thiệp hay không.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** LLM-as-Judge thỉnh thoảng trả về văn bản dài dòng thay vì chỉ trả về một con số duy nhất, gây ra lỗi crash hệ thống khi cố gắng chuyển đổi (cast) dữ liệu sang kiểu `float`.

**Symptom:**
Trong các lượt test Sprint 2, pipeline đôi khi bị ngắt quãng với lỗi `ValueError: could not convert string to float: 'Score: 0.9'`. Điều này khiến supervisor không thể lưu log và không thể xác định liệu có cần kích hoạt cơ chế HITL (Human-in-the-loop) hay không.

**Root cause:**
Dù `JUDGE_PROMPT` đã yêu cầu "CHỈ trả về một con số duy nhất", nhưng các mô hình LLM (đặc biệt là gpt-4o-mini) đôi khi vẫn tự động thêm các tiền tố như "Confidence score:" hoặc "0.9 (Based on context)".

**Cách sửa:**
Tôi đã nhập module `re` (Regular Expression) và sử dụng hàm `re.search(r"([0-9]*\.[0-9]+|[0-9]+)", score_str)` để trích xuất chính xác con số đầu tiên tìm thấy trong chuỗi trả về của LLM. Đồng thời, tôi thêm các hàm bọc `min(1.0, max(0.0, confidence))` để đảm bảo dữ liệu luôn nằm trong khoảng hợp lệ.

**Bằng chứng trước/sau:**
- Trước: `float("Score: 0.8")` -> Crash.
- Sau: `re.search` trích xuất được `0.8`, hệ thống chạy ổn định 100% các query test.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã thiết kế hệ thống Prompt chặt chẽ, đặc biệt là `SYSTEM_PROMPT` với các quy tắc nghiêm ngặt về trích dẫn nguồn và từ chối trả lời khi thiếu dữ liệu, giúp giảm thiểu tối đa hiện tượng "bịa" thông tin.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Phần xử lý lỗi khi gọi API OpenAI (`_call_llm`) hiện tại chỉ đang trả về chuỗi trống hoặc thông báo lỗi đơn giản, chưa có cơ chế retry hoặc fallback sang mô hình khác nếu gặp lỗi quota/network.

**Nhóm phụ thuộc vào tôi ở đâu?**
Toàn bộ output cuối cùng mà người dùng nhìn thấy đều đi qua module của tôi. Nếu module Synthesis lỗi hoặc không kịp hoàn thiện, hệ thống sẽ chỉ dừng lại ở bước tìm kiếm mà không đưa ra được lời khuyên hành động cụ thể cho người dùng.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc hoàn toàn vào chất lượng chunks từ Tuấn và logic kiểm tra ngoại lệ từ Hải. Nếu Tuấn lấy sai tài liệu, câu trả lời của tôi dù "ngọt" đến đâu cũng sẽ là thông tin sai.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ cải tiến tính năng trích dẫn tài liệu (Citation) bằng cách yêu cầu LLM chỉ rõ chính xác đoạn văn (snippet) nào trong context được dùng để trả lời câu hỏi, thay vì chỉ cite tên file ở cuối. Qua trace của các câu hỏi phức tạp (như "Quy trình escalate P1"), tôi thấy người dùng mất nhiều thời gian để đối chiếu lại thông tin nếu file tài liệu dài, việc có snippet dẫn chứng sẽ tăng độ tin cậy rõ rệt.

---

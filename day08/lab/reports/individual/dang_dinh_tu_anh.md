# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Đặng Đinh Tú Anh  
**Vai trò trong nhóm:** Core AI (index sanity + telemetry hardening + anti-hallucination grading)  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi tập trung vào ba mảng chính trong pipeline.

**Sprint 1 — Implement TODO trong `index.py`:** Hoàn thiện toàn bộ các TODO của Sprint 1.

- `preprocess_document()`: implement parse metadata từ header (Source, Department, Effective Date, Access) bằng line-by-line matching, tách nội dung chính khỏi header, normalize khoảng trắng thừa (`\n{3,}` → `\n\n`).
- `chunk_document()`: implement split theo heading pattern `=== ... ===`, sau đó gọi `_split_by_size()` cho từng section. Mỗi chunk giữ đầy đủ metadata gốc và bổ sung field `section`.
- `_split_by_size()`: implement ghép paragraph đến gần `chunk_chars`, cắt mềm tại ranh giới tự nhiên (`\n\n`, `.`, ` `), và thêm overlap bằng cách lấy đuôi chunk trước vào đầu chunk kế.
- `list_chunks()` và `inspect_metadata_coverage()`: implement in preview chunk với metadata đầy đủ, đếm phân bố theo department, đếm chunk thiếu `effective_date`.
- Cấu hình `CHUNK_SIZE = 400` token, `CHUNK_OVERLAP = 80` token theo khuyến nghị slide.
- Bổ sung guard kiểm tra đầu vào: null/empty doc raise `ValueError` hoặc trả list trống; tài liệu dưới 100 ký tự in `[WARN]`.

Đồng thời viết ghi chú rebuild index trong `README.md` và chuẩn hóa file `test_questions_normalized.json`.

**Giai đoạn 3 — Telemetry hardening:** Cùng phối hợp chuẩn hóa tên field trong `extra` của `run_telemetry.py` (`ok` → `success`, `error` → `error_type`), bổ sung comment cho pricing env vars, và thêm secret-filter để ngăn `api_key` hay `hf_token` lọt vào `logs/runs.jsonl`.

**Grading rubric:** Viết `grade_rubric.py` — script chấm điểm 10 grading questions theo thang Full/Partial/Zero/Penalty, xử lý đặc biệt câu abstain (gq07), log kết quả ra JSONL và CSV.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

**Chunking là điểm nghẽn thầm lặng nhất của RAG.** Trước lab, tôi nghĩ chunking chỉ là "cắt text". Sau khi đọc kỹ `_split_by_size()`, tôi hiểu rằng nếu cắt sai vị trí — ví dụ cắt ngay giữa danh sách ngoại lệ trong Điều 3 của chính sách hoàn tiền — thì retriever có thể lấy đúng file nhưng thiếu nửa nội dung, khiến model tưởng thông tin đầy đủ mà trả lời thiếu. Đây chính là failure mode của gq03. Việc ưu tiên cắt tại `\n\n` và boundary tự nhiên, kết hợp overlap, không phải thừa mà là bảo vệ tính liên tục ngữ nghĩa.

**Secret leaking trong log là rủi ro thực tế.** Khi thêm `HF_TOKEN` vào `.env`, tôi nhận ra nếu caller vô tình truyền `{"hf_token": ..., "query": ...}` vào `finish()`, token sẽ bị ghi thẳng vào `logs/runs.jsonl` — file không nằm trong `.gitignore` theo từng dòng. Filter theo tên key là phòng thủ đơn giản nhưng cần thiết.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều ngạc nhiên nhất là **gq07 (abstain) cần thang điểm hoàn toàn khác** với 9 câu còn lại. Ban đầu tôi tính dùng chung multiplier (Full=100%, Partial=50%), nhưng với câu hỏi không có expected source, "Full" không có nghĩa là trả lời đúng 100% criteria — mà là "nói rõ không có thông tin". Nếu áp thang % thì câu abstain mơ hồ (Partial) sẽ cho 50% × 10 = 5 điểm, trùng với thang tuyệt đối. Nhưng câu Penalty (bịa con số) cần cố định −5 bất kể điểm max, vì đây là penalty cứng chứ không phải −50% × 10. Việc tách riêng `ABSTAIN_GRADE_POINTS` cho gq07 giải quyết sự không nhất quán này.

Khó khăn nhỏ hơn: chuẩn hóa test questions đòi hỏi đọc kỹ từng câu — nhiều thay đổi trông giống typo nhưng thực ra là lỗi nhất quán ngữ nghĩa (ví dụ `"hàng kỹ thuật số"` vs `"sản phẩm kỹ thuật số"` trong cùng một câu hỏi/đáp án).

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** gq07 — "Công ty sẽ phạt bao nhiêu nếu team IT vi phạm cam kết SLA P1?"

**Phân tích:**

Đây là câu "hallucination bait" — thông tin về mức phạt vi phạm SLA không có trong bất kỳ tài liệu nào được index. Pipeline baseline có xu hướng trả lời theo general knowledge về SLA penalty (ví dụ đề cập "theo thông lệ ngành" hoặc tự suy ra con số), không nói rõ đây là thông tin ngoài phạm vi tài liệu. Điểm baseline ở mức Zero hoặc Penalty nếu bịa con số.

Lỗi nằm ở tầng **generation**: retriever thực ra không tìm thấy chunk nào liên quan vì không có chunk nào chứa "mức phạt SLA" — đây là tín hiệu đúng. Nhưng prompt baseline không đủ chặt ở nhánh "context rỗng hoặc không liên quan", khiến model tự lấp đầy bằng prior knowledge.

Sau khi harden abstain path (Task A) — thêm điều kiện explicit trong prompt: nếu không có chunk nào có độ liên quan đủ cao, phải nêu rõ "Tài liệu hiện có không đề cập" — pipeline trả về grade Full (abstain rõ ràng). Variant không thay đổi gì về retrieval mode mà chỉ thay đổi generation guard, đúng nguyên tắc A/B một biến.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thử **metadata-aware filtering** ở bước retrieval: khi câu hỏi chứa thông tin thời gian (ví dụ "trước ngày 01/02/2026"), tự động thêm filter `effective_date` vào ChromaDB query thay vì để model tự suy. Kết quả eval cho thấy gq10 (temporal scoping) là failure mode điển hình khi retriever lấy nhầm chunk từ phiên bản cũ của policy. Filter metadata sẽ cắt bỏ chunk lỗi thời trước khi vào reranker — đây là cải thiện tầng retrieval, không đụng generation, đúng tinh thần A/B một biến.

# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Hoàng Long  
**MSHV:** 2A202600160  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi đảm nhận vai trò **Eval Owner** — chịu trách nhiệm xây dựng bộ câu hỏi test, hệ thống chấm điểm tự động, và script chạy pipeline.

**Sprint 1:** Tôi đọc kỹ 5 tài liệu trong `data/docs/` (chính sách hoàn tiền, SLA, quyền truy cập, FAQ helpdesk, nghỉ phép) để hiểu domain. Rà soát 10 câu mẫu có sẵn trong `test_questions.json`. Sau đó soạn thêm 9 câu bổ sung trong `test_questions_extra.json` với 3 mức độ (easy/medium/hard), bao gồm cả câu yêu cầu so sánh multi-section (eq07), inference từ ngưỡng (eq08), và cross-doc reasoning (eq09).

**Sprint 2:** Xây dựng `run_test.py` — script chạy tự động toàn bộ bộ câu hỏi qua pipeline RAG, hỗ trợ chọn bộ câu hỏi (`--all`, `--extra`), đổi retrieval mode (`--mode hybrid`), bật rerank (`--rerank`), và xuất log theo format `grading_run.json`.

**Sprint 3:** Implement 3 hàm scoring bằng **LLM-as-Judge** trong `eval.py`: `score_faithfulness()`, `score_answer_relevance()`, `score_completeness()`, cùng 2 helper functions (`_call_judge_llm()` hỗ trợ OpenAI/Gemini, `_parse_judge_response()` parse JSON robust).

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Concept tôi hiểu rõ nhất là **evaluation pipeline trong RAG** — cụ thể là sự khác biệt giữa 4 metrics:

- **Faithfulness** đo generation quality: answer có bám đúng context được retrieve hay bịa thêm. Đây là metric phát hiện hallucination.
- **Context Recall** đo retrieval quality: retriever có mang về đúng tài liệu cần thiết không. Metric này không liên quan đến LLM mà chỉ đánh giá vector search.
- **Answer Relevance** đo xem answer có đúng trọng tâm câu hỏi không — khác với faithfulness vì answer có thể faithful (bám context) nhưng irrelevant (lạc đề).
- **Completeness** so sánh với ground truth để xem có thiếu thông tin quan trọng không.

Điều quan trọng tôi nhận ra: 4 metrics này phải dùng kết hợp. Một answer có faithfulness=5 nhưng completeness=2 nghĩa là model trả lời đúng nhưng thiếu — vấn đề nằm ở retrieval (không lấy đủ evidence), không phải ở generation.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất là **parse response từ LLM judge**. Khi implement `_parse_judge_response()`, tôi nhận ra LLM không phải lúc nào cũng trả về JSON sạch — đôi khi nó wrap trong markdown code block ````json ... `````, đôi khi thêm text giải thích trước JSON, hoặc trả về JSON với key khác ("notes" thay vì "reason"). Tôi phải viết 4 tầng fallback: (1) parse trực tiếp, (2) extract từ code block, (3) regex tìm `{"score": ...}` trong text, (4) regex tìm pattern `X/5`.

Điều ngạc nhiên là **câu abstain** (q09 — ERR-403-AUTH) lại khó chấm hơn tôi nghĩ. Prompt judge phải được thiết kế cẩn thận: nếu câu hỏi không có trong docs và model đúng khi nói "không đủ thông tin", thì relevance score phải là 5 (đúng hành vi), không phải 1. Tôi đã thêm note đặc biệt trong prompt của `score_answer_relevance()` để handle case này.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 — "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Đây là câu khó nhất trong bộ test vì "Approval Matrix" là **tên cũ** của tài liệu, trong khi tài liệu hiện tại có tên "Access Control SOP" (`access_control_sop.txt`). Dòng ghi chú trong file: *"Tài liệu này trước đây có tên 'Approval Matrix for System Access'"*.

**Pipeline trả lời đúng/sai phụ thuộc vào retrieval strategy:**

- **Dense search (baseline):** Có khả năng fail vì embedding của "Approval Matrix" không gần embedding của "Access Control SOP" — hai cụm từ này hoàn toàn khác về mặt ngữ nghĩa bề mặt. Score context_recall có thể = 0 nếu retriever không lấy được `access_control_sop.txt`.

- **Hybrid search (variant):** BM25 component có thể match keyword "Approval Matrix" với dòng ghi chú trong file, giúp retrieve đúng tài liệu. Đây là lý do nhóm chọn hybrid làm variant — corpus có cả ngôn ngữ tự nhiên lẫn tên riêng/alias.

**Root cause nếu fail:** Lỗi nằm ở **retrieval** (dense bỏ lỡ alias), không phải indexing (metadata đầy đủ) hay generation (prompt đã có grounding rule). Fix cụ thể: dùng hybrid search hoặc query expansion để map "Approval Matrix" → "Access Control SOP".

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

**Cải tiến 1:** Thêm **weighted scoring** trong `score_context_recall()` — hiện tại mỗi expected source có trọng số bằng nhau, nhưng một số source quan trọng hơn (ví dụ q07 chỉ có 1 source, miss là mất toàn bộ evidence). Tôi sẽ thêm field `"primary_source"` trong test_questions.json và tính weighted recall.

**Cải tiến 2:** Implement **per-question comparison table** trong `run_test.py` — chạy cùng câu hỏi với 2 config (baseline và variant) side-by-side, in delta cho từng metric để nhanh chóng identify câu nào variant tốt hơn/kém hơn.

---

*File: `reports/individual/2A202600160_NguyenHoangLong.md`*

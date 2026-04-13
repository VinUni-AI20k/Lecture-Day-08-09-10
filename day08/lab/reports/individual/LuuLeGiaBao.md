# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Retrieval Owner  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi chịu trách nhiệm triển khai toàn bộ module `rag_answer.py` bao gồm Sprint 2 (Baseline) và Sprint 3 (Tuning). Cụ thể, tôi implement ba phương thức retrieval: (1) Dense retrieval sử dụng vector embedding từ ChromaDB, (2) Sparse retrieval dùng BM25 để tìm kiếm theo keyword chính xác, và (3) Hybrid retrieval kết hợp cả hai bằng Reciprocal Rank Fusion. Ngoài ra, tôi cũng implement reranking bằng cross-encoder và query transformation (expansion). Module cốt lõi là hàm `rag_answer()` - gọi retrieval → xây dựng context block → prompt grounded → gọi LLM. Công việc của tôi kết nối trực tiếp với output của index.py (ChromaDB) và input cho eval.py (test_questions.json, scorecard).

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Tôi hiểu rõ hơn về sự khác biệt giữa **dense vs. sparse retrieval** và tại sao kết hợp cả hai lại quan trọng. Dense retrieval (vector search) rất tốt ở việc nắm bắt _ý nghĩa ngữ cảnh_ nhưng dễ bỏ sót các _tên riêng_ như "ERR-403-AUTH" hay "License Key". Ngược lại, sparse retrieval (BM25) bắt được chính xác các thuật ngữ nhưng không hiểu sâu ý nghĩa. Khi kết hợp bằng Reciprocal Rank Fusion, chúng ta được lợi ích của cả hai chiều. Điều khác tôi học là **grounded prompt** không chỉ đơn thuần là đưa context vào; mà cần kỷ luật output ("only from context", "cite sources", "abstain if unsure") để tránh hallucination. Độc quyền: đơn giản hóa prompt lại có thể tăng faithfulness.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều ngạc nhiên nhất là variant hybrid + rerank **không cải thiện** so với baseline dense đơn giản (4.2 → 4.0 faithfulness, 4.6 → 4.3 relevance). Ban đầu tôi giả thuyết hybrid sẽ bắt được những câu hỏi keyword-heavy mà dense miss. Nhưng kết quả cho thấy thêm complexity lại giảm hiệu suất. Debug lâu nhất là lỗi "collection not found" khi hybrid retrieval cố truy cập ChromaDB — phải kiểm tra CHROMA_DB_DIR path. Độc quyền khác: BM25 rất nhạy cảm với tokenization; ngôn ngữ tiếng Việt không word-boundary rõ ràng. Mỗi tham số (top_k, weights, K parameter) thay đổi đều có thể tạo hiệu ứng bất ngờ.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 — "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Baseline trả lời: "Approval Matrix để cấp quyền hệ thống là tài liệu trước đây có tên 'Approval Matrix for System Access'". Điểm: Faithfulness=4/5 (chỉ đúng một phần), Relevance=5/5, Completeness=3/5.

Lỗi chủ yếu ở **retrieval**: tài liệu gốc được đổi tên từ "Approval Matrix for System Access" thành "Access Control SOP" nhưng model không trích dẫn tên mới này. Dense retrieval chỉ nhận được "tên cũ" mà không fetch được context về rename.

Variant hybrid + rerank cũng fail tương tự (Faithfulness=2/5, tệ hơn). Lý do: BM25 có thể match keyword "Approval Matrix" nhưng không hiểu được rằng đó là alias cũ. Thậm chí (cross-encoder) rerank còn làm tệ hơn vì model confuse với alias/outdated info.

**Kết luận:** Vấn đề không phải là algorithm mà là **indexing metadata**: tài liệu thiếu field "alias" hoặc "previous_name" để tracking rename. Nếu có metadata này, retrieval sẽ tốt hơn.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thêm **metadata field "alias"** vào ChromaDB chunk và implement **semantic similarity matching trên alias** vì q07 failed chính vì alias query. Thứ hai, tôi sẽ tune lại **hybrid weights** (đang 60% dense / 40% sparse) bằng cách chạy grid search trên dev set, vì kết quả cho thấy hybrid hiện tại không tham gia enough. Thứ ba, tôi sẽ thêm **query fallback**: nếu LLM trả về "Tôi không biết" (q09, q10), hệ thống tự động thử lại với query expansion strategy khác thay vì bỏ cuộc ngay.

---

_Lưu file này với tên: `reports/individual/[ten_ban].md`_
_Ví dụ: `reports/individual/nguyen_van_a.md`_

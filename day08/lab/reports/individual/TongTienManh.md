# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Tống Tiến Mạnh 
**Vai trò trong nhóm:** Tech Lead
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi đảm nhận Sprint 1 và Sprint 2, tức là toàn bộ phần nền tảng của pipeline RAG.

**Sprint 1 — Build index (`index.py`):** Tôi implement `preprocess_document()` để extract metadata (source, department, effective_date, access) từ header file bằng regex, `chunk_document()` để tách tài liệu theo heading `=== Section ===`, sau đó gọi `_split_by_size()` với CHUNK_SIZE = 400 tokens và CHUNK_OVERLAP = 80 tokens. Hàm `get_embedding()` dùng model `text-embedding-3-small` qua API shopaikey. Cuối cùng `build_index()` upsert toàn bộ chunks vào ChromaDB persistent với cosine similarity.

**Sprint 2 — Retrieval & Generation (`rag_answer.py`):** Tôi implement `retrieve_dense()` embed query rồi query ChromaDB, `build_context_block()` đóng gói chunks có đánh số [1][2][3] để model trích dẫn, `build_grounded_prompt()` theo 4 quy tắc evidence-only / abstain / citation / short, `call_llm()` dùng GPT-4o temperature=0 qua cùng API, và hàm `rag_answer()` nối toàn bộ 4 bước thành pipeline.

Code của tôi là đầu vào trực tiếp cho Sprint 3 (hybrid/rerank của thành viên khác) và Sprint 4 (eval.py import `rag_answer` để chấm điểm).

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

**Chunking theo cấu trúc tự nhiên vs. cắt theo ký tự cứng**

Trước lab, tôi nghĩ chunk đơn giản là cắt text mỗi N token. Sau khi implement `chunk_document()`, tôi hiểu tại sao cần ưu tiên cắt theo heading và paragraph: nếu cắt giữa một điều khoản (ví dụ: "ticket P1 có SLA 15 phút... " bị cắt đôi), retriever sẽ kéo về chunk thiếu thông tin, LLM không đủ evidence để trả lời đúng. Code dùng `=== Section ===` làm ranh giới đầu tiên, rồi mới dùng `\n\n` và cuối cùng mới cắt theo ký tự — ba tầng ưu tiên.

**Grounded prompt và abstain logic**

Implement `build_grounded_prompt()` giúp tôi hiểu cụ thể: câu prompt cần ra lệnh rõ ràng "chỉ trả lời từ context", "nếu thiếu thì nói không biết", và "gắn số [1][2] khi trích dẫn". Không có ba dòng lệnh đó, model sẽ tự suy diễn từ training data. Scorecard cho thấy Faithfulness đạt 4.60/5 ở baseline — điều này xác nhận prompt grounding có tác dụng rõ ràng.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

**Vấn đề API key không được inject vào environment**

Hàm `get_embedding()` ban đầu chỉ dùng `os.getenv("SHOPAIKEY_API_KEY")`. Khi chạy từ terminal trên Windows, biến chưa được load đúng cách, dẫn đến `ValueError: Thiếu SHOPAIKEY_API_KEY`. Tôi phải thêm fallback: nếu `os.getenv()` trả về `None`, đọc trực tiếp bằng `dotenv_values(ENV_PATH)`. Giả thuyết ban đầu của tôi là `load_dotenv()` ở đầu file đã đủ — thực tế không phải lúc nào cũng vậy trên Windows khi script được gọi từ ngoài.

**Context Recall = 5.00 nhưng Relevance chỉ 3.00**

Điều ngạc nhiên là retriever kéo đúng source (recall hoàn hảo) nhưng Relevance lại thấp, đặc biệt q06 (Escalation P1) chỉ 1/5. Tôi xem lại và phát hiện: chunk chứa đoạn mô tả quy trình escalation bị lẫn với phần header metadata của doc, khiến LLM tạo ra câu trả lời đúng source nhưng không trực tiếp trả lời câu hỏi. Đây là bài học về tầm quan trọng của chất lượng chunk, không chỉ là số lượng chunks được retrieve.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 — "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Đây là câu được ghi chú rõ trong `test_questions.json` là "query alias/tên cũ — thử nghiệm hybrid retrieval": user hỏi bằng tên cũ "Approval Matrix" trong khi doc đổi tên thành "Access Control SOP" (file `access-control-sop.md`).

**Baseline (dense only):** Faithfulness=5, Relevance=3, Recall=5, Completeness=4. Retriever vẫn tìm được đúng source vì embedding semantic đủ gần giữa "Approval Matrix" và "Access Control SOP". Tuy nhiên Relevance chỉ 3 — câu trả lời chưa giải thích rõ sự đổi tên, chỉ trả về thông tin trong chunk mà không nối hai tên lại.

**Variant (dense + rerank):** Faithfulness=4, Relevance=4, Recall=5, Completeness=4. Relevance tăng từ 3→4 nhờ rerank chọn được chunk chứa đoạn giải thích rõ hơn về alias. Nhưng Faithfulness lại giảm từ 5→4 — rerank đôi khi chọn chunk thiếu grounding hơn so với top-1 dense.

**Lỗi nằm ở:** Generation — prompt không hướng dẫn model giải thích sự thay đổi tên tài liệu khi phát hiện alias. Retrieval không phải vấn đề vì Recall=5 ở cả hai. Cải tiến đề xuất: thêm instruction trong prompt: "Nếu query dùng tên cũ của tài liệu, hãy ghi rõ tên hiện tại."

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

**1. Cải thiện chunking cho section có metadata header lẫn vào nội dung**, vì scorecard cho thấy q06 (Escalation P1) có Relevance = 1 ở cả baseline và variant — đây là dấu hiệu chunk bị nhiễu từ phần header, không phải lỗi retrieval (Recall = 5). Tôi sẽ thêm bước strip metadata lines khỏi section body trước khi tạo chunk.

**2. Thêm `query_transform="expansion"` vào baseline config**, vì q07 (Approval Matrix alias) cho thấy dense retrieval đã tìm được source nhưng Relevance chỉ 3 — query expansion có thể sinh thêm alias "Access Control SOP" giúp retriever kéo về chunk có context đầy đủ hơn, từ đó generation trả lời rõ ràng hơn.

---


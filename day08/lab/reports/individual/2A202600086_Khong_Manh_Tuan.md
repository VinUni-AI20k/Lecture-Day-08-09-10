# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Không Mạnh Tuấn  
**Vai trò trong nhóm:** Retrieval Owner / Eval Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi chịu trách nhiệm chính ở hai mảng: **tuning retrieval pipeline** và **cải thiện hệ thống đánh giá (eval)**.

Về retrieval, tôi phân tích kết quả scorecard baseline và variant để xác định root cause từng vấn đề, sau đó điều chỉnh ba tham số: tăng `TOP_K_SEARCH` từ 10 lên 15 (pool rộng hơn cho câu hỏi multi-section), tăng `TOP_K_SELECT` từ 3 lên 5 (đủ context cho câu hỏi cross-document), và tăng `dense_weight` từ 0.6 lên 0.7 trong hybrid retrieval để giảm nhiễu từ BM25. Đồng thời tôi cải thiện `build_grounded_prompt` bằng cách bổ sung rule COMPLETENESS, làm mềm rule ABSTAIN, và thêm hướng dẫn trả lời bằng tiếng Việt.

Về eval, tôi phát hiện và sửa hai lỗi logic trong `eval.py`: hàm `score_context_recall` trả về điểm 5 thay vì `None` cho các câu hỏi không có expected sources, và `score_faithfulness` không phân biệt giữa "abstain question không có context" với "pipeline lỗi retrieval".

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Điều tôi hiểu rõ nhất sau lab là **sự tách biệt giữa retrieval quality và generation quality** trong đánh giá RAG.

Trước khi làm lab, tôi nghĩ nếu pipeline trả lời sai thì phần lớn là do retriever không tìm được đúng tài liệu. Nhưng khi nhìn vào kết quả, `Context Recall = 5.00/5` ở tất cả các cấu hình — tức là retriever đã lấy đúng source — nhưng câu trả lời vẫn thiếu hoặc sai ở gq05, gq08, gq09. Vấn đề thực sự nằm ở **chunking**: chunk bị cắt giữa thông tin quan trọng khiến LLM không thấy được URL đổi mật khẩu, số điện thoại hotline, hay yêu cầu training bắt buộc của Admin Access.

Điều này cho thấy pipeline RAG cần được nhìn nhận theo từng tầng riêng biệt: indexing → retrieval → selection → generation. Điểm kém ở generation không nhất thiết nghĩa là retrieval tệ — rất có thể chunk đúng được retrieve nhưng bị cắt mất phần quan trọng nhất.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều gây ngạc nhiên nhất là **gq10 có Faithfulness = 1 nhưng Relevance = 5 và Completeness = 5** trong cùng một lần chấm điểm. Về mặt logic, nếu câu trả lời hoàn toàn sai (fabricated) thì không thể đồng thời vừa trả lời đúng câu hỏi vừa bao phủ đủ nội dung. Đây là biểu hiện của **LLM judge inconsistency** — judge đọc nhầm cấu trúc câu "áp dụng cho...là Phiên bản 3" thành "Phiên bản 4 áp dụng cho đơn hàng trước ngày 01/02/2026".

Khó khăn lớn nhất là phân biệt khi nào điểm thấp là do retrieval mode, khi nào là do prompt, khi nào là do chunking. Ban đầu tôi nghĩ gq01 regression trên variant (hybrid đột ngột trả lời "Not enough data") là do prompt quá strict về ABSTAIN. Nhưng khi phân tích kỹ hơn, nguyên nhân là `dense_weight=0.6` quá thấp khiến BM25 noise đẩy chunk SLA ra khỏi top-3 — không phải lỗi prompt.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** gq05 — *"Contractor từ bên ngoài công ty có thể được cấp quyền Admin Access không? Nếu có, cần bao nhiêu ngày và có yêu cầu đặc biệt gì?"*

**Phân tích:**

Đây là câu hỏi thú vị nhất vì nó có `Context Recall = 5` — retriever đã lấy đúng file `access-control-sop.md` — nhưng cả baseline lẫn variant đều không trả lời được đầy đủ (Relevance = 1, Completeness = 1 ở baseline; Relevance = 3, Completeness = 2 ở variant).

Nguyên nhân: thông tin cần thiết nằm ở **hai section khác nhau** trong cùng một file — Section 1 xác nhận scope áp dụng cho contractor, Section 2 mô tả Level 4 (Admin Access) cần IT Manager + CISO duyệt, 5 ngày xử lý, và training bắt buộc. Với `top_k_select=3`, chỉ một trong hai section được đưa vào prompt. LLM thấy thiếu thông tin nên abstain.

Sau khi tăng `top_k_select` lên 5, variant cải thiện lên Relevance = 3, Completeness = 2 — tức là bắt đầu nhận ra contractor được cấp quyền, nhưng vẫn thiếu chi tiết 5 ngày và training. Để giải quyết triệt để, cần fix ở tầng **chunking**: tăng chunk size hoặc dùng parent-child chunking để giữ nguyên Section 2 không bị cắt. Đây là trường hợp điển hình cho thấy retrieval tốt nhưng chunking kém vẫn làm hỏng kết quả cuối.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thử **parent-child chunking** cho `access-control-sop.md` và `helpdesk-faq.md`: chia nhỏ để embed (child chunk ~200 token) nhưng khi retrieve thì trả về cả section cha (~500 token) để LLM thấy đủ context. Kết quả eval hiện tại cho thấy gq05, gq08, gq09 đều bị điểm thấp vì chunk bị cắt giữa thông tin quan trọng — đây là bằng chứng rõ ràng để justify thay đổi chunking strategy thay vì tiếp tục tune retrieval parameters.

---

*Lưu file: `reports/individual/2A202600086_Khong_Manh_Tuan.md`*

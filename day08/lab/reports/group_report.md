# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** E403 Team 61  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Nguyen Duc Anh | Tech Lead / Retrieval Integration | ndaismeee@gmail.com |
| Do Minh Hieu | Indexing Owner (Sprint 1) | Dohieunt1102@gmail.com |
| Khuong Quang Vinh | Retrieval Owner (Dense/Sparse/Hybrid) | vinhkhuongquang@gmail.com |
| Nguyen Tien Dung | Generation Owner (Prompt + LLM) | dungnguyentien138@gmail.com |
| Tran Long Hai | Eval Owner (Sprint 4) | longhai7803@gmail.com |

**Ngày nộp:** 13/04/2026  
**Repo:** https://github.com/NDAismeee/E403_Team61

---

## 1. Pipeline nhóm đã xây dựng

Nhóm xây dựng pipeline RAG theo chuỗi: chuẩn hóa tài liệu -> chunk -> embedding -> lưu vector DB -> retrieve -> generate có citation -> evaluate. Dữ liệu nguồn là 5 tài liệu nội bộ (refund policy, SLA P1, access control SOP, IT helpdesk FAQ, HR leave policy), được index vào ChromaDB collection `rag_lab`.

Về chunking, nhóm thống nhất theo hướng heading-aware trước, sau đó tách theo độ dài để tránh cắt đứt ý nghiệp vụ. Cấu hình ổn định dùng trong toàn buổi lab là chunk size 400 tokens, overlap 80 tokens, giúp cân bằng giữa độ tập trung ngữ nghĩa và khả năng giữ ngữ cảnh liên đoạn. Embedding được thiết kế theo provider linh hoạt: OpenAI `text-embedding-3-small` khi có key và local sentence-transformer khi cần chạy fallback.

Ở pha retrieval, baseline dùng dense search (top_k_search=10, top_k_select=3). Variant Sprint 3 mà nhóm chọn là hybrid retrieval (dense + BM25 + RRF) để xử lý tốt hơn các câu hỏi có alias/keyword cụ thể. Trên generation, prompt được ràng buộc evidence-only, citation và abstain khi thiếu dữ liệu để giảm hallucination.

**Chunking decision:** 400/80, heading-based + split theo kích thước.  
**Embedding model:** OpenAI `text-embedding-3-small` (fallback local multilingual MiniLM).  
**Retrieval variant (Sprint 3):** Hybrid (Dense + Sparse BM25 + RRF), chọn vì corpus có cả câu mô tả tự nhiên và mã/thuật ngữ kỹ thuật.

---

## 2. Quyết định kỹ thuật quan trọng nhất

**Quyết định:** Chọn Hybrid Retrieval làm variant Sprint 3 (đổi duy nhất retrieval_mode từ dense sang hybrid).

**Bối cảnh vấn đề:**  
Trong baseline dense, nhóm quan sát hiện tượng nhiều câu đã retrieve đúng nguồn nhưng câu trả lời vẫn thiếu ý hoặc trả lời an toàn quá mức. Đồng thời với các query thiên về alias/keyword (ví dụ “Approval Matrix”, mã lỗi, tên điều khoản), dense đôi khi không ổn định bằng truy hồi keyword.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Giữ Dense + tinh chỉnh prompt | Dễ triển khai, ít thay đổi pipeline | Không xử lý triệt để câu query thiên keyword/alias |
| Hybrid (Dense + BM25 + RRF) | Kết hợp ngữ nghĩa và keyword, phù hợp mixed corpus | Tăng độ phức tạp, cần tuning trọng số/rank fusion |

**Phương án đã chọn và lý do:**  
Nhóm chọn Hybrid vì muốn cải thiện độ bao phủ truy hồi mà vẫn giữ dense làm trụ cột ngữ nghĩa. Cách hợp nhất theo RRF giúp giảm lệch thang điểm giữa dense và BM25, ổn định hơn so với cộng score trực tiếp.

**Bằng chứng từ scorecard/tuning-log:**  
Theo tuning log và grading logs, baseline dense có trung bình: Faithfulness 4.80, Relevance 2.40, Context Recall 5.00, Completeness 2.10. Variant hybrid có: 4.70, 2.30, 5.00, 2.10. Điều này cho thấy recall vốn đã cao, còn nút thắt lớn hơn nằm ở generation tổng hợp hơn là retrieve coverage.

---

## 3. Kết quả grading questions

**Ước tính điểm raw:** 80 / 98

**Câu tốt nhất:** ID: gq04  
**Lý do:** Câu về store credit 110% được hệ thống trả lời đúng, đủ ý, bám sát policy và đạt tổng điểm tối đa trong log (20/20 theo 4 metrics nội bộ của scorecard).

**Câu fail:** ID: gq02  
**Root cause:** Câu hỏi cần tổng hợp đa tín hiệu (remote + VPN + giới hạn thiết bị) từ nhiều đoạn. Retrieval có lấy đúng nguồn nhưng generation chưa tổng hợp đầy đủ nên relevance/completeness thấp.

**Câu gq07 (abstain):**  
Pipeline xử lý đúng hướng abstain: trả lời không tìm thấy thông tin về mức phạt vi phạm SLA P1 trong tài liệu hiện có. Đây là hành vi an toàn, trung thực với context rỗng/không đủ chứng cứ.

---

## 4. A/B Comparison — Baseline vs Variant

**Biến đã thay đổi (chỉ 1 biến):** `retrieval_mode`: dense -> hybrid

| Metric | Baseline | Variant | Delta |
|--------|---------|---------|-------|
| Faithfulness | 4.80 | 4.70 | -0.10 |
| Answer Relevance | 2.40 | 2.30 | -0.10 |
| Context Recall | 5.00 | 5.00 | 0.00 |
| Completeness | 2.10 | 2.10 | 0.00 |

**Kết luận:**  
Variant hybrid không vượt baseline trên bộ grading hiện tại. Kết quả A/B cho thấy việc đổi retrieval mode chưa tạo cải thiện đầu ra cuối cùng vì bài toán chính nằm ở generation policy (khuynh hướng abstain quá sớm hoặc chưa tổng hợp tốt evidence đa đoạn). Baseline dense hiện là cấu hình ổn định hơn để nộp trong bối cảnh thời gian giới hạn.

---

## 5. Phân công và đánh giá nhóm

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Do Minh Hieu | Indexing pipeline, metadata mapping, Chroma build/debug | Sprint 1 |
| Khuong Quang Vinh | Dense/Sparse/Hybrid retrieval core | Sprint 2-3 |
| Nguyen Tien Dung | Grounded prompt, LLM provider call, abstain/citation behavior | Sprint 2-3 |
| Tran Long Hai | Evaluation framework, scorecard metrics, grading logs | Sprint 4 |
| Nguyen Duc Anh | Tech lead, tích hợp nhánh và tuning variant end-to-end | Cross-sprint |

**Điều nhóm làm tốt:**  
Tách nhiệm vụ rõ theo sprint, có loop A/B đo đạc thật bằng log và scorecard, xử lý nhiều lỗi thực tế (env, API key, embedding dimension mismatch) mà vẫn giữ pipeline chạy end-to-end.

**Điều nhóm làm chưa tốt:**  
Thời gian dành cho tuning generation còn ít; có giai đoạn team tập trung nhiều vào retrieval trong khi điểm số cho thấy nút thắt nằm ở answer synthesis và prompt strategy.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì?

Nhóm sẽ ưu tiên một vòng tuning generation có kiểm soát (không đổi retrieval): chuẩn hóa prompt theo format bắt buộc trích dẫn từng claim, giảm false-abstain, và thêm bước kiểm tra answer-consistency trên top chunks. Song song, nhóm thử variant rerank (giữ retrieval_mode cố định) để xem có tăng relevance/completeness cho các câu multi-signal như gq02/gq03 hay không. Mục tiêu là biến context recall cao hiện tại thành cải thiện thực sự ở chất lượng câu trả lời cuối.

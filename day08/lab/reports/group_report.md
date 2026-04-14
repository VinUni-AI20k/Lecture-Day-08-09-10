# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** E3-C401  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Hoàng Kim Trí Thành | Tech Lead | hoangkimtrithanh@gmail.com |
| Quách Gia Dược | Retrieval Owner | quachgiaduoc2004@gmail.com |
| Phạm Quốc Dũng | Eval Owner | phamquocdung2109@gmail.com |
| Nguyễn Thành Nam | Documentation Owner | nguyenthanhnam2512@gmail.com |
| Đặng Đình Tú Anh | Core AI | anhscientist2202@gmail.com |

**Ngày nộp:** 13/04/2026  
**Repo:** https://github.com/jot2003/Lab8-Lab9-Lab10_C401_E3  
**Độ dài khuyến nghị:** 600–900 từ

---

## 1. Pipeline nhóm đã xây dựng (150–200 từ)

Nhóm xây dựng pipeline RAG theo luồng: người dùng đặt câu hỏi → embed query → truy vấn ChromaDB → chọn context phù hợp → dựng grounded prompt → gọi LLM → trả answer kèm citation `[n]`. Ở tầng indexing, nhóm dùng chunking theo section heading (`=== ... ===`) rồi cắt mềm theo paragraph/câu, với cấu hình khoảng `~400 tokens` và `~80 tokens overlap`; sau khi build index có tổng 29 chunk từ 5 tài liệu chính sách nội bộ. Mỗi chunk giữ metadata như `source`, `section`, `effective_date` để phục vụ freshness và trace nguồn.

Embedding model mặc định là OpenAI `text-embedding-3-small` (hoặc local model khi chạy local mode). Retrieval baseline của nhóm là dense cosine search; sau tuning, production config là `top_k_search=20`, `top_k_select=8`, `use_rerank=False`, `threshold=0.05`. Ở generation, nhóm dùng `gpt-4o-mini` (temperature=0) với prompt v2 có rule chống hallucination, bắt buộc citation theo snippet, và rule xử lý câu cross-section/cross-document.

**Chunking decision:**  
Nhóm chọn chunk nhỏ vừa phải + overlap để tránh cắt đôi điều khoản quan trọng, đặc biệt các câu hỏi cần tổng hợp nhiều section như gq05.

**Embedding model:**  
OpenAI `text-embedding-3-small` cho bản production; local embedding dùng cho môi trường không có API.

**Retrieval variant (Sprint 3):**  
Nhóm có implement hybrid/rerank nhưng chọn dense optimized làm production vì kết quả scorecard tốt và ổn định hơn trên bộ grading.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Giữ production retrieval là **dense optimized** thay vì chuyển sang hybrid.

**Bối cảnh vấn đề:**  
Baseline dense (`k_search=10`, `k_select=3`, `threshold=0.15`) bị hụt điểm vì thiếu context cho các câu multi-section và có false abstain ở gq05. Nhóm đứng trước lựa chọn: chuyển hẳn sang hybrid/rerank để tăng recall, hoặc giữ dense nhưng tăng độ phủ retrieval và chỉnh prompt/guard.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Dense + tăng `top_k_select`, giảm threshold | Ít thay đổi kiến trúc, dễ kiểm soát, giảm false abstain | Context dài hơn, cần prompt chặt để tránh loãng |
| Hybrid (dense+BM25) +/− rerank | Bắt keyword alias tốt hơn, hữu ích cho query đặc thù | Dễ kéo noise từ BM25, score scale khác làm tuning khó |

**Phương án đã chọn và lý do:**  
Nhóm chọn dense optimized: `top_k_search=20`, `top_k_select=8`, `threshold=0.05`, prompt v2. Lý do chính là hiệu quả thực tế tốt hơn trên bộ 10 câu grading, đồng thời giữ pipeline ổn định và dễ giải thích trong report.

**Bằng chứng từ scorecard/tuning-log:**  
Theo scorecard, raw score tăng từ `69/98` lên `83/98` (+14), projected từ `21.1/30` lên `25.4/30`. Hai lỗi lớn được sửa trực tiếp: gq05 (Zero→Full) và gq09 (Partial→Full). Các số liệu này khớp với `results/scorecard_baseline.md`, `results/scorecard_variant.md` và `docs/tuning-log.md`.

---

## 3. Kết quả grading questions (100–150 từ)

**Ước tính điểm raw:** 83 / 98

**Câu tốt nhất:** ID: gq05 — Lý do: cải thiện mạnh nhất (Zero→Full) sau khi tăng `top_k_select` và giảm threshold, giúp pipeline lấy đủ cả scope + detail section thay vì abstain sai.

**Câu fail:** ID: không có câu Zero ở variant; các câu còn Partial là gq02, gq04, gq06. Root cause chủ yếu nằm ở retrieval ranking/citation attribution (LLM gom citation, bỏ sót ext. 9999).

**Câu gq07 (abstain):** Pipeline xử lý đúng: trả lời "Không đủ dữ liệu trong tài liệu để trả lời.", không bịa mức phạt và không phát sinh penalty hallucination.

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

**Biến đã thay đổi (chỉ 1 biến):**  
Về mặt chiến lược retrieval: thử `retrieval_mode dense` so với `hybrid` ở setup single-variable để kiểm tra effect của strategy.  
Ở production tuning cuối cùng, nhóm tối ưu dense bằng thay đổi tham số retrieval depth/threshold theo evidence scorecard.

| Metric | Baseline | Variant | Delta |
|--------|---------|---------|-------|
| Faithfulness | 4.90 | 5.00 | +0.10 |
| Relevance | 4.20 | 5.00 | +0.80 |
| Context Recall | 4.44 | 4.89 | +0.44 |
| Completeness | 4.10 | 4.70 | +0.60 |

**Kết luận:**  
Variant production (dense optimized) tốt hơn baseline ở toàn bộ 4 metric. Điểm quan trọng nhất là giảm lỗi thiếu context ở các câu multi-section/cross-doc. Nhóm vẫn ghi nhận hybrid có lợi thế cho một số alias query, nhưng trên bộ grading hiện tại dense optimized cho chất lượng tổng thể cao hơn và ổn định hơn nên được chọn làm cấu hình chốt.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Hoàng Kim Trí Thành | Điều phối, review/merge, tích hợp và chốt config production | Sprint 2-4 |
| Đặng Đình Tú Anh | Core AI: harden abstain, citation grounding, grading artifacts | Sprint 3-4 |
| Quách Gia Dược | Retrieval flow, trace pipeline, tuning-log evidence | Sprint 3 |
| Phạm Quốc Dũng | Eval/scorecard formatting, grading report export | Sprint 4 |
| Nguyễn Thành Nam | Quick start, troubleshooting, chuẩn hóa docs | Sprint 4 |

**Điều nhóm làm tốt:**  
Chia việc rõ theo vai trò, merge theo đợt, và luôn có evidence định lượng (scorecard/A-B) trước khi chốt quyết định kỹ thuật.

**Điều nhóm làm chưa tốt:**  
Một số nhánh cập nhật artifact chưa đồng bộ thời điểm, dẫn đến phải rà lại commit khá nhiều trước khi chốt báo cáo cuối.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nhóm sẽ tập trung xử lý 3 câu Partial còn lại (gq02, gq04, gq06) bằng 2 hướng có bằng chứng: (1) cải thiện citation attribution cho câu cross-document; (2) tăng khả năng đưa chi tiết “peripheral” như hotline/ext vào answer mà không làm tăng hallucination. Đồng thời chạy lại benchmark cố định seed/config để kiểm tra mức cải thiện thật trước khi thay đổi production.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*

# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** Team 62  
**Thành viên:**

| Tên | Vai trò | Email |
|-----|---------|-------|
| Phan Thanh Sang | Tech Lead | sang.phan2409@gmail.com |
| Đỗ Minh Khiêm | Indexing Owner | dokhiem562@gmail.com |
| Trần Tiến Dũng | Retrieval Owner (Dense & Prompt) | tiendungtran2005@gmail.com |
| Ngô Hải Văn | Retrieval Owner (Hybrid & Rerank) | van.nh120802@gmail.com |
| Trần Đình Minh Vương | Eval & Docs Owner | vuongsky55.cv@gmail.com |

**Ngày nộp:** 2026-04-13  
**Repo:** https://github.com/hvan128/team62-lecture-Day-08-09-10
**Độ dài:** ~850 từ

---

## 1. Pipeline nhóm đã xây dựng

Nhóm triển khai đầy đủ pipeline RAG qua 4 sprint: `index.py` để preprocess/chunk/embed/upsert vào ChromaDB, `rag_answer.py` để retrieve + grounded generation, và `eval.py` để chấm scorecard baseline/variant và so sánh A/B. Dữ liệu gồm 5 tài liệu nghiệp vụ (refund, SLA P1, access control, helpdesk FAQ, HR policy), index thành 29 chunks có metadata để phục vụ citation và kiểm tra freshness.
Luồng chạy end-to-end của nhóm là: build index một lần, sau đó chạy query qua retriever, chọn top chunks, dựng grounded prompt, rồi generate answer có nguồn trích dẫn. Cách tách rõ từng tầng giúp nhóm debug nhanh theo Error Tree khi quality giảm (indexing, retrieval, hoặc generation).

**Chunking decision:**  
Nhóm dùng chunk theo section header (`=== ... ===`), `chunk_size=400`, `overlap=80` để giữ trọn ý theo điều khoản và giảm việc cắt ngữ cảnh giữa các rule/exception.

**Embedding model:**  
OpenAI `text-embedding-3-small` với ChromaDB (cosine similarity). Lý do chọn là môi trường đồng nhất cho cả nhóm, giảm sai lệch khi chạy eval trên nhiều máy.

**Retrieval variant (Sprint 3):**  
Nhóm chọn **Hybrid retrieval** (Dense + BM25 + RRF, weight 0.6/0.4) vì corpus vừa có câu tự nhiên vừa có keyword/alias như P1, Level 3, ERR-403.
Nhóm không bật rerank ở bản so sánh chính để giữ đúng nguyên tắc A/B "chỉ đổi một biến". Nhờ vậy, tác động tăng/giảm metric có thể quy trực tiếp về retrieval strategy thay vì nhiễu bởi nhiều thay đổi cùng lúc.

---

## 2. Quyết định kỹ thuật quan trọng nhất

**Quyết định:** Chốt baseline **Dense** làm cấu hình mặc định cho demo/grading, thay vì Hybrid.

**Bối cảnh vấn đề:**  
Trong Sprint 3, nhóm thấy Hybrid cải thiện một số câu hỏi alias/keyword, nhưng đồng thời tăng rủi ro retrieve nhiễu ở các câu có từ khóa phổ biến. Nhóm cần chọn giữa hai mục tiêu: (1) tăng coverage/relevance nhẹ, hoặc (2) giữ faithfulness ổn định để tránh hallucination/grounding sai.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Dense | Faithfulness ổn định hơn, grounding chặt | Có thể hụt alias/keyword đặc thù |
| Hybrid (0.6/0.4) | Relevance/Completeness nhỉnh hơn nhẹ | Dễ kéo chunk nhiễu, giảm faithfulness |

**Phương án đã chọn và lý do:**  
Nhóm chọn Dense cho bản nộp vì tiêu chí ưu tiên là đúng theo chứng cứ. Trong bài lab này, trade-off của Hybrid chưa đủ tốt để đánh đổi độ ổn định. Hybrid được giữ làm hướng cải tiến tiếp theo bằng cách giảm sparse weight và chỉ bật rerank sau khi kiểm soát retrieval noise.

**Bằng chứng từ scorecard/tuning-log:**  
Faithfulness baseline 4.50/5 cao hơn variant 4.30/5; Context Recall đều 5.00/5; Relevance/Completeness của variant chỉ tăng nhẹ (+0.10 mỗi metric). Ở `q07`, variant tụt faithfulness rõ (5 -> 2), phản ánh vấn đề grounding khi xử lý alias.

---

## 3. Kết quả grading questions

**Ước tính điểm raw:** ước tính mức trung bình-khá (theo `results/grading_report.md`, chưa quy đổi chính thức theo rubric full/partial/penalty của giảng viên).

**Câu tốt nhất:** ID `gq03` hoặc `gq10` — pipeline trả lời đúng trọng tâm exception/temporal scope, điểm các metric ổn định giữa baseline và variant. Ở các câu này, câu trả lời bám sát policy text và ít gặp lỗi suy diễn thêm ngoài context.

**Câu fail:** ID `gq05` — điểm thấp ở cả hai cấu hình, root cause chủ yếu ở retrieval/completeness: câu hỏi cần nhiều điều kiện (scope + approver + thời gian + training) nhưng câu trả lời chưa cover đủ. Đây là dạng câu multi-condition nên nếu top-k chọn thiếu một chunk quan trọng thì output dễ thiếu ý.

**Câu gq07 (abstain):**  
Pipeline xử lý đúng tinh thần abstain: không bịa mức phạt SLA khi tài liệu không có thông tin penalty, giúp tránh lỗi hallucination nặng.
Nhóm đánh giá đây là điểm cộng quan trọng vì rubric phạt rất nặng nếu model tự bịa con số. Việc giữ được "không biết" đúng ngữ cảnh giúp bảo toàn độ tin cậy của toàn hệ thống.

---

## 4. A/B Comparison — Baseline vs Variant

**Biến đã thay đổi (chỉ 1 biến):** `retrieval_mode` từ `dense` sang `hybrid` (các tham số khác giữ nguyên).

| Metric | Baseline | Variant | Delta |
|--------|---------|---------|-------|
| Faithfulness | 4.50/5 | 4.30/5 | -0.20 |
| Answer Relevance | 4.30/5 | 4.40/5 | +0.10 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 4.10/5 | 4.20/5 | +0.10 |

**Kết luận:**  
Variant chưa vượt baseline toàn diện. Hybrid hữu ích cho một vài câu alias/thiếu context, nhưng làm giảm độ ổn định grounding ở các câu access control. Nhóm chốt Dense làm cấu hình nộp; Hybrid giữ cho vòng tuning tiếp theo (0.8/0.2 + rerank có kiểm soát).
Từ góc nhìn vận hành, nhóm ưu tiên cấu hình có hành vi ổn định và dễ giải trình trước giảng viên hơn là cấu hình có tăng điểm nhẹ nhưng rủi ro answer lệch evidence.

---

## 5. Phân công và đánh giá nhóm

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Phan Thanh Sang | Setup môi trường, nối pipeline, smoke test end-to-end | 1, 2 |
| Đỗ Minh Khiêm | Preprocess/chunk/metadata schema, build index | 1 |
| Trần Tiến Dũng | Dense retrieval, grounded prompt, LLM call | 2 |
| Ngô Hải Văn | Hybrid/BM25/RRF, tuning log và phân tích trade-off | 3 |
| Trần Đình Minh Vương | Eval script, scorecard, A/B export, docs tổng hợp | 3, 4 |

**Điều nhóm làm tốt:**  
Giữ đúng A/B rule (đổi 1 biến), có bằng chứng định lượng qua scorecard, và phối hợp rõ trách nhiệm theo sprint nên kịp hoàn thành end-to-end.
Ngoài ra, nhóm tách vai trò retrieval dense và retrieval hybrid thành hai owner riêng nên vừa chạy được baseline sớm, vừa có thời gian tuning variant trước khi vào Sprint 4.

**Điều nhóm làm chưa tốt:**  
Chưa chạy đủ vòng tuning sâu cho hybrid; một số câu multi-condition vẫn thiếu completeness; khâu đồng bộ số liệu giữa các tài liệu ban đầu còn lệch và phải chỉnh cuối sprint.
Nếu quản lý thời gian tốt hơn, nhóm nên khóa mốc "freeze số liệu" sớm hơn để tránh cập nhật chéo giữa scorecard, architecture, tuning-log và group report ở phút cuối.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì?

Ưu tiên 1: chạy Variant 2 với `dense_weight=0.8`, `sparse_weight=0.2` để giảm retrieval noise nhưng vẫn giữ lợi ích keyword match.  
Ưu tiên 2: thêm cross-encoder rerank cho top-k select và test lại riêng các câu khó (`gq05`, `gq07`) nhằm tăng completeness mà không làm giảm faithfulness.
Ưu tiên 3: bổ sung một bộ regression mini (5 câu đại diện) để mỗi lần đổi retrieval config có thể kiểm tra nhanh trước khi chạy full 10 câu, giúp giảm rủi ro drift quality.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo `SCORING.md`*

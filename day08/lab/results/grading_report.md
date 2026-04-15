# Grading Questions Report

Ngày chạy: 2026-04-14  
Nguồn câu hỏi: data/grading_questions.json  
Số câu: 10

## 1. Cấu hình đã test

### Baseline
- retrieval_mode: dense
- top_k_search: 10
- top_k_select: 3
- use_rerank: False
- prompt_version: v1

### Variant (cũ — Hybrid + Rerank, không cải thiện)
- retrieval_mode: hybrid
- top_k_search: 10
- top_k_select: 3
- use_rerank: True

### Variant C (cải tiến — Dense + Prompt v2)
- retrieval_mode: dense
- top_k_search: 10
- top_k_select: **5** ↑
- use_rerank: False
- prompt_version: **v2** ↑

**Lý do chọn Variant C thay vì Hybrid+Rerank:**  
Context Recall = 5.0 ở cả hai cấu hình cũ → bottleneck là generation, không phải retrieval.
Tăng top_k_select 3→5 để đủ context cho câu hỏi multi-section (gq05, gq06).
Prompt v2 bổ sung 3 quy tắc cứng: COMPLETENESS, ABSTAIN, EMERGENCY path.

## 2. Kết quả tổng quan

| Metric | Baseline (Dense v1) | Variant (Hybrid+Rerank) | Variant C (Dense v2) | Delta (C - Baseline) |
|---|---:|---:|---:|---:|
| Faithfulness | 4.00 | 4.20 | **4.50** | **+0.50** |
| Relevance | 4.60 | 3.40 | **4.70** | **+0.10** |
| Context Recall | 5.00 | 5.00 | 5.00 | 0.00 |
| Completeness | 3.60 | 2.60 | **3.90** | **+0.30** |

Kết luận nhanh:
- Variant C cải thiện 3/4 metrics; Context Recall giữ nguyên (đã tối ưu).
- Faithfulness tăng +0.50: gq05 từ 2→5, gq06 từ 4→5.
- Completeness tăng +0.30: gq05 (4→5), gq08 (3→4).
- Abstain (gq07) hoạt động đúng — trả lời "Thông tin này không có trong tài liệu hiện có."

## 3. Kết quả theo từng câu hỏi

| ID | Baseline (F/R/CR/C) | Variant C (F/R/CR/C) | Nhận xét |
|---|---|---|---|
| gq01 | 5 / 5 / 5 / 4 | 5 / 5 / 5 / 3 | Baseline nhỉnh completeness |
| gq02 | 4 / 5 / 5 / 3 | 4 / 5 / 5 / 3 | Tương đương |
| gq03 | 4 / 5 / 5 / 4 | **5 / 5 / 5 / 5** | Variant tốt hơn |
| gq04 | 5 / 5 / 5 / 5 | 5 / 5 / 5 / 5 | Tương đương, tốt |
| gq05 | 2 / 5 / 5 / 4 | **5 / 5 / 5 / 5** | Cải thiện lớn — training bắt buộc được nêu đủ |
| gq06 | 4 / 5 / 5 / 4 | **5 / 5 / 5 / 4** | Faithfulness tăng — emergency path đúng |
| gq07 | 5 / 1 / N/A / 1 | 5 / 2 / N/A / 2 | Abstain đúng; relevance tăng nhẹ |
| gq08 | 4 / 5 / 5 / 3 | 4 / 5 / 5 / **4** | Completeness tốt hơn |
| gq09 | 2 / 5 / 5 / 3 | 2 / 5 / 5 / 3 | Tương đương |
| gq10 | 5 / 5 / 5 / 5 | 5 / 5 / 5 / 5 | Tương đương, tốt |

Ghi chú cột điểm:
- F: Faithfulness | R: Relevance | CR: Context Recall | C: Completeness

## 4. Phân tích root cause và fix

**gq05 (F: 2→5, C: 4→5):**  
Root cause: top_k_select=3 thiếu Section 1 (scope: contractor được phép) và yêu cầu
training bắt buộc của Level 4. Hai mảnh thông tin nằm ở hai chunk khác nhau trong access_control_sop.  
Fix: top_k_select=5 + prompt v2 yêu cầu liệt kê đầy đủ → đủ 4/4 grading criteria.

**gq06 (F: 4→5):**  
Root cause: prompt v1 không nhận diện "2 giờ sáng" như signal emergency → LLM mô tả quy trình
thường thay vì emergency escalation path (Section 4).  
Fix: prompt v2 có rule EMERGENCY/KHẨN CẤP → ưu tiên section đúng.

**gq07 (Abstain — C: 1→2):**  
Root cause: prompt v1 quá chung chung, LLM đưa ra câu trả lời mơ hồ thay vì abstain rõ.  
Fix: prompt v2 có quy tắc ABSTAIN cứng + low-score guard (top_score < 0.35) làm lớp bảo vệ thứ hai.

## 5. Điểm còn cần cải thiện

1. **gq07 Relevance (2/5)**: LLM-judge penalize abstain là "không trả lời câu hỏi". Cần custom judge prompt nhận diện "correct abstain = relevant answer".
2. **gq09 Faithfulness (2/5)**: Với top_k=5 thêm chunks ngoài helpdesk-faq, model có thể cite thêm thông tin không liên quan. Test top_k_select=4.
3. **gq01 Completeness (4→3)**: Variant hơi verbose; thiếu focus vào version history. Thêm instruction về version comparison vào prompt v2.

## 6. Tệp liên quan

- Bộ câu hỏi: data/grading_questions.json
- Scorecard baseline: results/scorecard_baseline.md
- Scorecard variant C: results/scorecard_variant.md
- A/B comparison: results/ab_comparison.csv
- Script chấm: eval.py
- Pipeline trả lời: rag_answer.py

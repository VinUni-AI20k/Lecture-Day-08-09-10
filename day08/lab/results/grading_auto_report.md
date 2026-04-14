# Chấm tự động — grading questions

> LLM-as-judge: **ước lượng** để benchmark nội bộ. Điểm chính thức do GV chấm theo [SCORING.md](../SCORING.md).

- **Config:** `dense | top_k_search=20 | top_k_select=8 | use_rerank=False | threshold=0.05 | prompt v2`
- **Tổng raw (ước lượng):** 83.0 / 98
- **Quy đổi 30 điểm:** 83/98 × 30 = **25.41/30**

## Chi tiết

| ID | Verdict | Điểm | Max | Lý do (rút gọn) |
|----|---------|:----:|:---:|-----------------|
| gq01 | Full | 10.0 | 10 | Nêu đúng SLA cũ (6h) và mới (4h), cite phiên bản v2026.1. Không bịa info thừa |
| gq02 | Partial | 5.0 | 10 | Đúng VPN bắt buộc + giới hạn 2 thiết bị. Thiếu citation từ 2 nguồn khác nhau |
| gq03 | Full | 10.0 | 10 | Nêu đủ 2 ngoại lệ (Flash Sale + đã kích hoạt) với citation |
| gq04 | Partial | 4.0 | 8 | Đúng 110% store credit, nhấn mạnh tùy chọn. Thiếu tên Điều 5 trong citation |
| gq05 | Full | 10.0 | 10 | Đầy đủ scope (contractor) + điều kiện Level 4 (IT Manager, CISO, 5 ngày, training) |
| gq06 | Partial | 6.0 | 12 | Đạt 4/5 tiêu chí escalation. Thiếu hotline on-call ext. 9999 từ SLA P1 |
| gq07 | Full | 10.0 | 10 | Abstain đúng — nêu rõ không có thông tin trong tài liệu, không bịa mức phạt |
| gq08 | Full | 10.0 | 10 | Phân biệt rõ nghỉ phép năm (báo trước 3 ngày) vs nghỉ ốm (giấy y tế) |
| gq09 | Full | 8.0 | 8 | Đúng 90 ngày + 7 ngày nhắc + URL SSO + ext. 9000 |
| gq10 | Full | 10.0 | 10 | Nêu rõ effective_date, phân biệt v3/v4 cho đơn trước 01/02 |

## Tóm tắt

| Verdict | Số câu |
|---------|:------:|
| Full | 7 |
| Partial | 3 |
| Zero | 0 |
| Penalty | 0 |

**Hallucination: 0 câu** — pipeline không bịa thông tin ở bất kỳ câu nào.

## So sánh Baseline vs Variant (optimized)

| | Baseline | Variant | Delta |
|---|:---:|:---:|:---:|
| Full | 5 | **7** | +2 |
| Partial | 4 | 3 | −1 |
| Zero | 1 | **0** | −1 |
| Raw score | 69/98 | **83/98** | **+14** |
| Projected /30 | 21.1 | **25.4** | **+4.3** |

### Câu cải thiện chính
1. **gq05** (Zero → Full, +10): hạ threshold 0.15→0.05 + tăng k_select 3→8 giải quyết false abstain.
2. **gq09** (Partial → Full, +4): k_select=8 kéo được chunk FAQ chứa URL SSO + ext. 9000.

### Câu vẫn Partial (cần cải thiện nếu có thêm thời gian)
1. **gq02**: cần citation từ 2 nguồn — LLM gom vào [1] dù info từ 2 doc khác nhau.
2. **gq04**: cần nêu tên "Điều 5" trong citation — LLM chỉ cite document name.
3. **gq06**: thiếu ext. 9999 — chunk chứa hotline xếp rank thấp (7/8), nằm ngoài vùng focus của LLM.

## Nguồn dữ liệu

- Đề + rubric: [`data/test/grading_questions.json`](../data/test/grading_questions.json)
- Log pipeline: [`logs/grading_run.json`](../logs/grading_run.json)
- Scorecard baseline: [`results/scorecard_baseline.md`](scorecard_baseline.md)
- Scorecard variant: [`results/scorecard_variant.md`](scorecard_variant.md)

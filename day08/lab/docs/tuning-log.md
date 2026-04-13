# Tuning Log — RAG Pipeline (Day 08 Lab)

> Mục tiêu commit này: ghi rõ setup A/B **đúng chuẩn chỉ đổi 1 biến** để nộp bài và truy vết.
> Lưu ý: thử nghiệm "hybrid + rerank" vẫn được giữ làm tham chiếu khám phá, nhưng không dùng làm A/B chính thức.

---

## 1) Baseline cố định (mốc so sánh)

Config baseline dùng xuyên suốt:

```
retrieval_mode = "dense"
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini (temperature=0)
```

Scorecard baseline: `results/scorecard_baseline.md`

---

## 2) Thử nghiệm khám phá (khong dung cho A/B chinh thuc)

Da chay bien the:

```
retrieval_mode = "hybrid"
top_k_search = 15
top_k_select = 4
use_rerank = True
```

Ly do giu lai muc nay:
- Dung de nhin nhanh headroom khi bat nhieu don bay retrieval cung luc.
- KHONG dung lam bang chung A/B chinh thuc vi da doi nhieu hon 1 bien.

---

## 3) A/B chuan cho nop bai (single-variable)

Bien thay doi duy nhat:

```
retrieval_mode: "dense" -> "hybrid"
```

Tat ca bien con lai giu nguyen:

```
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini
```

Bang setup A/B:

| Run label | retrieval_mode | top_k_search | top_k_select | use_rerank | So bien doi |
|---|---|---:|---:|---|---:|
| baseline_dense | dense | 10 | 3 | False | 0 |
| variant_hybrid_only | hybrid | 10 | 3 | False | 1 |

Ghi chu:
- Rule A/B duoc thoa: moi lan chi doi mot bien.
- Neu can thu rerank, tao mot lan A/B khac (dense no-rerank vs dense rerank).

---

## 4) Khung ghi ket qua cho lan chay A/B single-variable

| Metric | Baseline | Variant (hybrid only) | Delta |
|---|---:|---:|---:|
| Faithfulness | 5.00 | 5.00 | 0.00 |
| Relevance | 4.20 | 1.00 | -3.20 |
| Context Recall | 5.00 | 0.00 | -5.00 |
| Completeness | 4.10 | 1.20 | -2.90 |

Nguon dien so:
- `results/scorecard_baseline.md`
- `results/scorecard_variant.md`
- `results/ab_comparison.csv`

---

## 5) Ghi chu phan tich tam thoi

1. Ket qua thuc te cho thay `hybrid only` khong dat muc toi thieu cho A/B nay: relevance va context recall giam manh.
2. Variant tra ve abstain tren nhieu cau co du lieu, dan den context recall = 0.00 trong tong hop scorecard.
3. Quyet dinh cuoi: giu `baseline_dense` lam cau hinh nop bai/production hien tai.
4. Huong tiep theo: neu can danh lai hybrid, can tao A/B rieng voi du lieu va nguong retrieval da hieu chinh, sau do moi so sanh tiep.

---

## 6) Logic Abstain — Hardened Path (Task A)

### Mục tiêu
Đảm bảo pipeline **không bao giờ sinh ra con số, ngày tháng, tên, quy trình** mà không có nguồn trong tài liệu, kể cả khi retrieval trả về một số chunk có vẻ liên quan.

### Ba lớp bảo vệ

| Lớp | Vị trí | Điều kiện trigger |
|-----|--------|-------------------|
| L1 — Empty retrieve | `rag_answer_impl` / `rag_answer_stream` | `candidates == []` sau retrieval |
| L2 — Weak score guard | `rag_answer_impl` / `rag_answer_stream` | `max(score) < WEAK_CONTEXT_SCORE_THRESHOLD` (mặc định 0.15) |
| L3 — Prompt rule | `build_grounded_prompt` | LLM được yêu cầu tuyệt đối không bịa specifics; mọi claim phải có `[n]` |

### Ngưỡng `WEAK_CONTEXT_SCORE_THRESHOLD = 0.15`
- Dense/Hybrid score = `1 − cosine_distance` ∈ [0, 1].
- Score < 0.15 nghĩa là chunk gần như không liên quan về mặt ngữ nghĩa.
- BM25 raw score thường > 1 khi có keyword hit → ngưỡng này không ảnh hưởng BM25.
- Có thể ghi đè bằng biến môi trường `WEAK_CONTEXT_SCORE_THRESHOLD`.

### Cấu hình ghi đè
```
WEAK_CONTEXT_SCORE_THRESHOLD=0.20  # chặt hơn
WEAK_CONTEXT_SCORE_THRESHOLD=0.10  # lỏng hơn
```

---

## 7) Citation Grounding — Format bắt buộc (Task B)

### Quy tắc
- **Mọi claim thực tế** (số, ngày, tên, quy trình) phải kèm `[n]` tương ứng với snippet số `n` trong context block.
- Câu trả lời có nội dung nhưng thiếu citation bị coi là vi phạm grounding.
- Prompt rule 5 bây giờ phát biểu rõ: *"Answers without citations are not allowed when context is available."*

### Ví dụ TRƯỚC (vi phạm — không citation)

> **Q:** SLA xử lý ticket P1 là bao lâu?
>
> **A (BAD):** Ticket P1 có SLA phản hồi ban đầu 15 phút và thời gian xử lý 4 giờ.

Câu trả lời trên chứa số liệu nhưng không có `[1]` hay `[2]` → người đọc không thể truy nguồn.

### Ví dụ SAU (đúng chuẩn — có citation)

> **A (GOOD):** Theo tài liệu [1], ticket P1 có SLA phản hồi ban đầu **15 phút** và thời gian xử lý (resolution) **4 giờ**.

### Ví dụ abstain đúng chuẩn

> **Q:** ERR-403-AUTH là lỗi gì và cách xử lý?
>
> **A (GOOD):** Không đủ dữ liệu trong tài liệu để trả lời.

Không thêm bất kỳ chi tiết nào về lỗi auth dù model "biết" về HTTP 403 từ pretrain.

---

## 8) Bảng so sánh A/B — Baseline vs Variant (Task E)

### Config

| Tham số | Baseline | Variant |
|---------|----------|---------|
| `retrieval_mode` | `dense` | **`hybrid`** |
| `top_k_search` | 10 | 10 |
| `top_k_select` | 3 | 3 |
| `use_rerank` | False | False |
| `llm_model` | gpt-4o-mini | gpt-4o-mini |
| **Số biến đổi** | 0 | **1** |

Biến duy nhất thay đổi: `retrieval_mode` từ `dense` → `hybrid` (dense + BM25 + RRF).

### Kết quả đo (10 câu hỏi, mỗi metric thang 1–5)

| Metric | Baseline (dense) | Variant (hybrid only) | Delta |
|--------|:----------------:|:---------------------:|:-----:|
| Faithfulness | **5.00** | **5.00** | 0.00 |
| Relevance | **4.20** | 1.00 | −3.20 |
| Context Recall | **5.00** | **0.00** | −5.00 |
| Completeness | **4.10** | 1.20 | −2.90 |

Nguồn số liệu: `results/scorecard_baseline.md`, `results/scorecard_variant.md`, `logs/runs.jsonl`.

### Kết luận — Vì sao giữ Baseline dense

1. **Faithfulness bằng nhau (5.0/5):** cả hai config đều grounded hoàn toàn — không sinh thông tin ngoài tài liệu.
2. **Baseline thắng lớn về Relevance (4.2 vs 1.0):** variant hybrid-only tra ve nhieu cau abstain, khong giai quyet dung trong tam cau hoi.
3. **Baseline thắng lớn về Context Recall (5.0 vs 0.0):** variant khong retrieve duoc expected sources tren cac cau co dap an.
4. **Baseline thắng rõ về Completeness (4.1 vs 1.2):** variant bo sot nhieu y chinh do context dau vao khong dat.
5. **Quyết định:** giữ `retrieval_mode = dense` làm config chốt cho nhánh hiện tại. `hybrid` se duoc danh gia lai trong mot sprint rieng sau khi khac phuc retrieval cho variant.

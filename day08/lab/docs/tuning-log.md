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
| Faithfulness | _dien sau khi chay_ | _dien sau khi chay_ | _dien sau khi chay_ |
| Relevance | _dien sau khi chay_ | _dien sau khi chay_ | _dien sau khi chay_ |
| Context Recall | _dien sau khi chay_ | _dien sau khi chay_ | _dien sau khi chay_ |
| Completeness | _dien sau khi chay_ | _dien sau khi chay_ | _dien sau khi chay_ |

Nguon dien so:
- `results/scorecard_baseline.md`
- `results/scorecard_variant.md`
- `results/ab_comparison.csv`

---

## 5) Ghi chu phan tich tam thoi

1. Dense on dinh o cau hoi de, nhung de bo sot alias/keyword hiem.
2. Hybrid ky vong tang kha nang lay dung ngu canh cho cau co alias.
3. Quyết định cuoi cung se chot o commit tiep theo dua tren bang before/after.

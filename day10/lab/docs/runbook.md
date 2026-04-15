# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

> User / agent thấy gì? (VD: trả lời “14 ngày” thay vì 7 ngày)

---

## Detection

> Metric nào báo? (freshness, expectation fail, eval `hits_forbidden`)

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/*.json` | … |
| 2 | Mở `artifacts/quarantine/*.csv` | … |
| 3 | Chạy `python eval_retrieval.py` | … |

---

## Mitigation

> Rerun pipeline, rollback embed, tạm banner “data stale”, …

---

## Prevention

> Thêm expectation, alert, owner — nối sang Day 11 nếu có guardrail.

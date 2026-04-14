# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** ___________  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| ___ | Tech Lead | ___ |
| ___ | Retrieval Owner | ___ |
| ___ | Eval Owner | ___ |
| ___ | Documentation Owner | ___ |

**Ngày nộp:** ___________  
**Repo:** ___________  
**Độ dài khuyến nghị:** 600–900 từ

---

> **Hướng dẫn nộp group report:**
>
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code, scorecard, hoặc tuning log** — không mô tả chung chung

---

## 1. Pipeline nhóm đã xây dựng (150–200 từ)

> Mô tả ngắn gọn pipeline của nhóm:
> - Chunking strategy: size, overlap, phương pháp tách (by paragraph, by section, v.v.)
> - Embedding model đã dùng
> - Retrieval mode: dense / hybrid / rerank (Sprint 3 variant)

**Chunking decision:**
> VD: "Nhóm dùng chunk_size=500, overlap=50, tách theo section headers vì tài liệu có cấu trúc rõ ràng."

_________________

**Embedding model:**

_________________

**Retrieval variant (Sprint 3):**
> Nêu rõ variant đã chọn (hybrid / rerank / query transform) và lý do ngắn gọn.

_________________

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất trong lab.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn.

**Quyết định:** ___________________

**Bối cảnh vấn đề:**

_________________

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| ___ | ___ | ___ |
| ___ | ___ | ___ |

**Phương án đã chọn và lý do:**

_________________

**Bằng chứng từ scorecard/tuning-log:**

_________________

---

## 3. Kết quả grading questions (100–150 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Câu nào pipeline xử lý tốt nhất? Tại sao?
> - Câu nào pipeline fail? Root cause ở đâu (indexing / retrieval / generation)?
> - Câu gq07 (abstain) — pipeline xử lý thế nào?

**Ước tính điểm raw:** ___ / 98

**Câu tốt nhất:** ID: ___ — Lý do: ___________________

**Câu fail:** ID: ___ — Root cause: ___________________

**Câu gq07 (abstain):** ___________________

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

> Dựa vào `docs/tuning-log.md`. Tóm tắt kết quả A/B thực tế của nhóm.

**Biến đã thay đổi (chỉ 1 biến):** ___________________

| Metric | Baseline | Variant | Delta |
|--------|---------|---------|-------|
| ___ | ___ | ___ | ___ |
| ___ | ___ | ___ | ___ |

**Kết luận:**
> Variant tốt hơn hay kém hơn? Ở điểm nào?

_________________

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| ___ | ___________________ | ___ |
| ___ | ___________________ | ___ |
| ___ | ___________________ | ___ |
| ___ | ___________________ | ___ |

**Điều nhóm làm tốt:**

_________________

**Điều nhóm làm chưa tốt:**

_________________

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> 1–2 cải tiến cụ thể với lý do có bằng chứng từ scorecard.

_________________

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*

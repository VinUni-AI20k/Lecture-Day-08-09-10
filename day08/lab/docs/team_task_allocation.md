# Phân công nhiệm vụ nhóm Day 08 (Core, không tính UI)

## Danh sách thành viên

1. Hoang Kim Tri Thanh (2A202600372)
2. Dang Dinh Tu Anh (2A202600019)
3. Quach Gia Duoc (2A202600423)
4. Pham Quoc Dung (2A202600490)
5. Nguyen Thanh Nam (2A202600205)


## Mục tiêu chia việc

- Mỗi người có phần việc riêng, dễ hiểu, tránh conflict.
- Chia nhỏ theo giai đoạn để tạo nhiều commit rõ nội dung.
- Tập trung vào core: indexing, retrieval, eval, telemetry, docs/runbook.

## Mục tiêu công việc (phiên bản dễ hiểu)

- Mục tiêu 1: Khi chạy hệ thống, bot trả lời đúng hơn và bớt bịa.
- Mục tiêu 2: Có log + report để chứng minh nhóm đã làm thật, không chỉ nói miệng.
- Mục tiêu 3: Mỗi thành viên đều có commit đúng phần của mình để thầy dễ chấm.
- Mục tiêu 4: Ưu tiên việc nhỏ, làm xong nhanh, commit ngay (không dồn việc đến cuối).
- Mục tiêu 5: Nhóm trưởng (Tri Thanh) tập trung điều phối, review và kết nối tiến độ, nên số commit có thể ít hơn các bạn khác.

## Quy ước commit chung (bắt buộc)

- Mỗi commit chỉ làm 1 việc nhỏ.
- Format:
  - `feat(day08-lab): ...`
  - `fix(day08-lab): ...`
  - `docs(day08-lab): ...`
  - `chore(day08-lab): ...`
- Mỗi thành viên tối thiểu 4-6 commit.
- Mỗi commit cần ghi rõ file đã sửa và cách test nhanh trong phần mô tả commit (1-2 dòng).

---

## Giai đoạn 1 - Ổn định dữ liệu và indexing (dễ, commit nhanh)

### Hoang Kim Tri Thanh - Nhóm trưởng (điều phối + hỗ trợ kỹ thuật)

**Vai trò chính (dễ hiểu):**
- Chia việc, chốt scope từng giai đoạn, nhắc deadline.
- Hỗ trợ khi bạn khác bị kẹt bug.
- Review nhanh commit trước khi merge để đảm bảo không conflict.

**File chính:** `day08/lab/docs/architecture.md`, `day08/lab/README.md`, hỗ trợ chọn lọc ở `day08/lab/index.py`

Task nhỏ theo commit:
1. Cập nhật sơ đồ và mô tả flow tổng trong `architecture.md` để cả nhóm bám theo.
2. Tạo checklist tiến độ theo giai đoạn trong `README.md` (ai làm gì, xong khi nào).
3. Hỗ trợ 1 chỉnh sửa nhỏ ở indexing nếu cần để unblock nhóm.
4. Viết commit tổng hợp nhỏ cho từng giai đoạn (chỉ phần docs/chore).

Commit gợi ý:
- `docs(day08-lab): clarify architecture flow for team execution`
- `docs(day08-lab): add phase checklist for team progress`
- `chore(day08-lab): sync minor integration notes after team updates`

### Dang Dinh Tu Anh - Hỗ trợ index + data sanity

**File chính:** `day08/lab/index.py`, `day08/lab/data/test_questions.json`

Task nhỏ theo commit:
1. Bổ sung validate input rỗng/null trước khi chunk.
2. Thêm cảnh báo khi tài liệu quá ngắn.
3. Rà soát 10 câu test và chuẩn hóa typo cho câu hỏi tiếng Việt.
4. Viết ghi chú ngắn trong README về cách rebuild index.

Commit gợi ý:
- `fix(day08-lab): handle empty docs before chunking`
- `chore(day08-lab): warn for short documents in indexing`
- `docs(day08-lab): add quick rebuild-index note`

---

## Giai đoạn 2 - Retrieval và answer quality

### Quach Gia Duoc - Owner Retrieval

**File chính:** `day08/lab/rag_answer.py`, `day08/lab/docs/tuning-log.md`

Task nhỏ theo commit:
1. Làm rõ flow chọn mode dense/sparse/hybrid (refactor code dễ đọc).
2. Cải thiện message khi không đủ dữ liệu (abstain rõ ràng).
3. Thêm/điều chỉnh trace step detail cho dễ debug.
4. Cập nhật `tuning-log.md` với 1-2 thử nghiệm retrieval.

Commit gợi ý:
- `refactor(day08-lab): simplify retrieval mode selection flow`
- `fix(day08-lab): improve abstain response when context is missing`
- `feat(day08-lab): enrich pipeline trace details for retrieval`
- `docs(day08-lab): add retrieval tuning notes`

### Pham Quoc Dung - Owner Evaluation

**File chính:** `day08/lab/eval.py`, `day08/lab/grade_grading_run.py`, `day08/lab/results/*`

Task nhỏ theo commit:
1. Làm rõ output scorecard (format bảng nhất quán).
2. Bổ sung check tránh chia 0/giá trị N/A.
3. Cập nhật export report markdown dễ đọc hơn.
4. Chạy lại grading và cập nhật file kết quả.

Commit gợi ý:
- `feat(day08-lab): improve scorecard markdown formatting`
- `fix(day08-lab): guard edge cases for delta and averages`
- `feat(day08-lab): refine grading report export`
- `chore(day08-lab): refresh grading result artifacts`

---

## Giai đoạn 3 - Logging, telemetry, docs vận hành

### Hoang Kim Tri Thanh + Dang Dinh Tu Anh (phối hợp nhẹ)

**File chính:** `day08/lab/run_telemetry.py`, `day08/lab/.env.example`

Task nhỏ theo commit:
1. Chuẩn hóa tên field telemetry trong `extra`.
2. Bổ sung comment ngắn cho pricing env vars.
3. Kiểm tra log không chứa secret.

Commit gợi ý:
- `feat(day08-lab): standardize telemetry extra fields`
- `docs(day08-lab): clarify telemetry pricing env variables`
- `fix(day08-lab): avoid sensitive values in logs`

### Nguyen Thanh Nam (non-tech) - Task siêu dễ

**File chính:** `day08/lab/README.md`, `day08/lab/docs/architecture.md`

Task nhỏ theo commit:
1. Cập nhật mục "Cách chạy nhanh" (copy/paste command).
2. Cập nhật mục "Lỗi thường gặp" (API chưa chạy, port bị chiếm, thiếu .env).
3. Chuẩn hóa format heading/bullet cho dễ đọc.
4. Rà lỗi chính tả tiếng Việt trong docs.

Commit gợi ý:
- `docs(day08-lab): add quick start commands`
- `docs(day08-lab): add common troubleshooting section`
- `docs(day08-lab): clean markdown headings and bullet consistency`
- `docs(day08-lab): fix vietnamese typos in lab docs`

Lưu ý cho Nam:
- Không cần sửa file `.py`.
- Chỉ sửa markdown (`.md`) để an toàn và dễ commit.

---

## Giai đoạn 4 - Tổng hợp và chốt điểm

### Người merge cuối: Pham Quoc Dung

Checklist chốt:
1. Chạy test tối thiểu:
   - `python day08/lab/eval.py`
   - `python day08/lab/grade_grading_run.py`
2. Kiểm tra log/report tạo thành công trong `day08/lab/results`.
3. Đảm bảo không commit `.env`, `chroma_db`, log runtime.
4. Ghi commit tổng hợp:
   - `chore(day08-lab): integrate team contributions and refresh reports`

## KPI commit đề xuất (để thầy dễ chấm phân công)

- Hoang Kim Tri Thanh (nhóm trưởng): 3 commits
- Dang Dinh Tu Anh: 4 commits
- Quach Gia Duoc: 5 commits
- Pham Quoc Dung: 5 commits
- Nguyen Thanh Nam: 4 commits (docs-only)

Tổng: khoảng 21 commit nhỏ, rõ nội dung và vai trò từng người.

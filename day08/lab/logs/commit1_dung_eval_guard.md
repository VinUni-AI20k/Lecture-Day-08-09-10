# Commit 1 Log - Pham Quoc Dung

## Thong tin

- Nhanh: feature/day08/dung-commit1-eval-guard
- Muc tieu: Guard edge cases cho delta va averages trong eval.
- Commit message du kien: fix(day08-lab): guard edge cases for delta and averages
- Ngay thuc hien: 2026-04-13

## File da sua

- lab/eval.py

## Noi dung da lam

1. Sua hien thi average trong `run_scorecard`:
   - Truoc: neu `avg = 0` se bi coi la false va in `N/A`.
   - Sau: dung dieu kien `avg is not None` de 0.00 van hien thi dung.

2. Sua hien thi A/B trong `compare_ab`:
   - `b_str` va `v_str` doi sang `is not None` de tranh sai khi gia tri = 0.

3. Sua phan summary markdown trong `generate_scorecard_summary`:
   - `avg_str` doi sang `is not None` de tranh in sai `N/A`.

## Cach test nhanh

- Lenh syntax:
  - `python -m py_compile lab/eval.py`
- Lenh chay eval (khi co API key):
  - `python lab/eval.py`

## Ket qua mong doi

- Khong con truong hop diem trung binh bang 0 bi hien thi thanh N/A.
- Bang A/B va scorecard markdown nhat quan hon cho edge case.

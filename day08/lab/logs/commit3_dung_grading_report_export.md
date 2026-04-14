# Commit 3 Log - Pham Quoc Dung

## Thong tin

- Nhanh: PhamQuocDung-2A202600490
- Muc tieu: Refine export report trong grade_grading_run.py
- Commit message: feat(day08-lab): refine grading report export
- Ngay thuc hien: 2026-04-13

## Kiem tra merge nhanh retrieval-flow

- Nhanh duoc yeu cau: feature/2a202600423-quachgiaduoc-retrieval-flow
- Ket qua: khong ton tai tren remote.
- Nhanh thay the ton tai: origin/QuachGiaDuoc-2A202600423
- Hanh dong: da merge vao nhanh hien tai.
- Ket qua conflict: khong co conflict.
- File thay doi sau merge: lab/docs/tuning-log.md, lab/rag_answer.py

## File da sua trong Commit 3

- lab/grade_grading_run.py

## Noi dung da lam

1. Them helper sanitize markdown cell de tranh vo bang khi co ky tu xuong dong hoac dau "|".
2. Them helper tinh ti le tieu chi dat (criteria hit ratio) cho tung cau.
3. Bo sung bang tong hop verdict (Full/Partial/Zero/Penalty/ERROR).
4. Nang cap bang chi tiet voi cot Criteria, Hallucination va ly do rut gon.
5. Bo sung thong tin metadata report: thoi diem chay, nguon de, nguon log.

## Cach test nhanh

- `python -m py_compile lab/grade_grading_run.py`

## Ket qua mong doi

- Report grading markdown de doc hon, de doi chieu hon.
- Bang markdown on dinh, han che vo cot do noi dung phuc tap.

# Quy trình test Day 09 (lab)

Làm **một lần** khi clone máy mới hoặc đổi key; sau đó lặp từ bước 3 khi sửa code.

## 1. Dùng chung OpenAI key với Day 8

Trong folder `day09/lab`, tạo `.env` bằng cách **copy file** từ Day 8 (không commit `.env`):

**PowerShell** (từ repo root):

```powershell
Copy-Item "day08\lab\.env" "day09\lab\.env"
```

Hoặc copy tay: `day08/lab/.env` → `day09/lab/.env`.

Day 9 đọc **`OPENAI_API_KEY`** (giống Day 8). `graph.py` và `eval_trace.py` tự `load_dotenv` file `day09/lab/.env`.

## 2. Build index vector (Chroma)

Chỉ cần khi **chưa có** `day09/lab/chroma_db` hoặc đổi file trong `data/docs/`:

```bash
cd day09/lab
python build_index.py
```

## 3. Smoke test graph

```bash
python graph.py
```

Kiểm tra: không lỗi import, có `route`, `workers_called`, trace trong `artifacts/traces/`.

## 4. Test 15 câu (public)

```bash
python eval_trace.py
```

- Đọc `data/test_questions.json`
- Mỗi câu: `run_graph` → lưu `artifacts/traces/run_*.json`
- Cuối cùng: in metrics + `artifacts/eval_report.json`

## 5. Phân tích trace đã chạy (không chạy lại pipeline)

```bash
python eval_trace.py --analyze
```

## 6. So sánh Day 08 vs Day 09 (baseline)

```bash
python eval_trace.py --compare
```

Cần có `day08/lab/results/grading_auto.json` (nếu có trong repo) để điền baseline.

## 7. Grading (sau khi có `grading_questions.json`)

```bash
python eval_trace.py --grading
```

Ghi `artifacts/grading_run.jsonl` — file nộp chấm điểm (theo `SCORING.md`).

## 8. Test từng worker riêng (tuỳ chọn)

```bash
python workers/retrieval.py
python workers/policy_tool.py
python workers/synthesis.py
```

---

**Tóm tắt:** `.env` (copy từ Day 8) → `build_index.py` (lần đầu) → `graph.py` → `eval_trace.py` → `--grading` khi có đủ câu chấm.

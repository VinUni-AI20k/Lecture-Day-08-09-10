# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

Agent hoặc người dùng nhận được câu trả lời sai từ hệ thống, ví dụ:

- Trả lời **"hoàn tiền trong 14 ngày"** thay vì 7 ngày
- Trả lời **"10 ngày phép năm"** thay vì 12 ngày (chính sách HR 2025 cũ)
- Không tìm được câu trả lời cho câu hỏi về SLA hoặc FAQ helpdesk
- Retrieval eval báo: `contains_expected=no` hoặc `hits_forbidden=yes`

---

## Detection

Các tín hiệu cảnh báo theo thứ tự ưu tiên kiểm tra:

| Tín hiệu                           | Nơi xem                 | Ý nghĩa                                                                    |
| ---------------------------------- | ----------------------- | -------------------------------------------------------------------------- |
| `freshness_check=FAIL`             | Log pipeline / manifest | Dữ liệu cũ hơn SLA (mặc định 24h) — vector store có thể chưa được cập nhật |
| `freshness_check=WARN`             | Log pipeline / manifest | Không đọc được timestamp — manifest thiếu trường `latest_exported_at`      |
| `freshness_check=PASS`             | Log pipeline / manifest | Dữ liệu còn mới, trong ngưỡng SLA                                          |
| `expectation[...] FAIL (halt)`     | Log pipeline            | Pipeline dừng, dữ liệu xấu không được embed                                |
| `expectation[...] FAIL (warn)`     | Log pipeline            | Cảnh báo nhưng pipeline vẫn tiếp tục                                       |
| `hits_forbidden=yes`               | `artifacts/eval/*.csv`  | Retrieval đang trả về chunk có nội dung sai (stale policy)                 |
| `quarantine_records` tăng đột biến | Log pipeline            | Nguồn export có vấn đề — nhiều dòng bị loại hơn bình thường                |

---

## Diagnosis

| Bước | Việc làm                                                       | Kết quả mong đợi                                                                   |
| ---- | -------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 1    | Mở `artifacts/manifests/manifest_<run_id>.json`                | Xem `cleaned_records`, `quarantine_records`, `latest_exported_at`, `no_refund_fix` |
| 2    | Mở `artifacts/quarantine/quarantine_<run_id>.csv`              | Xem cột `reason` — loại lỗi nào chiếm nhiều nhất                                   |
| 3    | Mở `artifacts/logs/run_<run_id>.log`                           | Tìm dòng `expectation[...] FAIL` hoặc `PIPELINE_HALT`                              |
| 4    | Chạy `python eval_retrieval.py --out artifacts/eval/debug.csv` | Xem `contains_expected` và `hits_forbidden` từng câu hỏi                           |
| 5    | So sánh `chunk_text` trong ChromaDB với `data/docs/*.txt`      | Phát hiện chunk stale chưa bị prune                                                |

**Debug order (theo slide Day 10):**

```
Freshness / version → Volume & errors → Schema & contract → Lineage / run_id → model/prompt
```

---

## Mitigation

**Trường hợp 1 — Dữ liệu stale (freshness FAIL):**

```bash
# Cập nhật exported_at trong CSV nguồn rồi chạy lại pipeline
python etl_pipeline.py run --run-id hotfix-$(date +%Y%m%d)
```

**Trường hợp 2 — Expectation FAIL / Pipeline bị halt:**

```bash
# Xem log để biết expectation nào fail
cat artifacts/logs/run_<run_id>.log | grep FAIL

# Sửa dữ liệu nguồn hoặc cleaning rules, rồi chạy lại
python etl_pipeline.py run --run-id fix-<run_id>
```

**Trường hợp 3 — Vector store còn chunk cũ (`hits_forbidden=yes`):**

```bash
# Chạy lại pipeline — cơ chế prune sẽ xóa vector không còn trong cleaned
python etl_pipeline.py run --run-id reindex-$(date +%Y%m%d)

# Xác nhận prune hoạt động: tìm dòng embed_prune_removed trong log
grep embed_prune_removed artifacts/logs/run_<run_id>.log
```

**Trường hợp 4 — Cần rollback khẩn cấp:**

- Dùng manifest của lần chạy trước để biết `cleaned_csv` cũ → chạy lại embed từ file đó.
- Hoặc tạm thời thông báo cho người dùng rằng thông tin đang được cập nhật.

---

## Prevention

1. **Thêm expectation halt** cho mọi rule mới — đảm bảo dữ liệu xấu bị chặn trước khi embed.
2. **Kiểm tra `freshness_check`** sau mỗi lần chạy pipeline — nếu FAIL liên tục cần điều chỉnh `FRESHNESS_SLA_HOURS` trong `.env` hoặc cập nhật tần suất export.
3. **Chạy `eval_retrieval.py`** sau mỗi lần reindex quan trọng để xác nhận retrieval không bị giảm chất lượng.
4. **Không dùng `--skip-validate`** trong môi trường production — flag này chỉ dành cho demo Sprint 3.
5. **Đồng bộ `ALLOWED_DOC_IDS`** trong `cleaning_rules.py` và `contracts/data_contract.yaml` mỗi khi thêm tài liệu mới.

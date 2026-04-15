# Day10 - Thứ tự ưu tiên task, người phải xong trước, và quy trình thực hiện

File này trả lời 3 câu hỏi quan trọng:
- Task nào ưu tiên cao nhất?
- Ai phải xong trước để người sau làm tiếp?
- Quy trình chuẩn từ lúc bắt đầu đến lúc merge/push?

---

## 1) Bản đồ task và owner

- `D10-T00` - Integration/Release gate - **Hoang Kim Tri Thanh**
- `D10-T01` - Ingestion + schema - **Dang Dinh Tu Anh**
- `D10-T02` - Cleaning + quarantine - **Quach Gia Duoc**
- `D10-T03` - Expectations + eval + grading - **Pham Quoc Dung**
- `D10-T04` - Runbook + architecture docs + report - **Nguyen Thanh Nam**
- `D10-T05` - Embed + freshness + runtime triage - **Hoang Kim Tri Thanh**

---

## 2) Thứ tự ưu tiên bắt buộc (critical path)

## P0 - Bắt buộc hoàn thành trước (nếu chưa xong thì các task sau dễ sai)

1. `D10-T01` (Ingestion + schema)
2. `D10-T02` (Cleaning + quarantine)
3. `D10-T05` (Embed + freshness)
4. `D10-T03` (Quality/eval/grading)
5. `D10-T04` (Docs/report theo artifact thật)
6. `D10-T00` (Release gate, chốt merge)

Giải thích ngắn:
- Không ingest ổn -> clean không có input đúng.
- Không clean ổn -> embed/eval sai nền dữ liệu.
- Không embed ổn -> eval/grading không phản ánh đúng.
- Docs phải đi sau artifact thật để tránh viết “không khớp thực tế”.

## P1 - Quan trọng nhưng có thể song song một phần

- `D10-T03` có thể chuẩn bị logic/format report sớm, nhưng chốt số liệu phải đợi sau `D10-T05`.
- `D10-T04` có thể viết khung runbook/architecture trước, nhưng nội dung cuối phải lấy từ run thật.

## P2 - Hoàn thiện/chốt điểm

- Chuẩn hóa wording docs, bổ sung hình/minh họa, polish báo cáo cá nhân.
- Các cải tiến không đổi core output.

---

## 3) Ai phải xong trước ai? (dependency rõ ràng)

## Luồng phụ thuộc chính

- **Tú Anh (`D10-T01`) phải xong trước Được (`D10-T02`)**
  - Vì `clean_rows()` cần input/schema ổn định.
- **Được (`D10-T02`) phải xong trước Tri Thanh (`D10-T05`)**
  - Vì embed dùng dữ liệu đã clean/quarantine.
- **Tri Thanh (`D10-T05`) phải xong vòng run ổn trước Dũng (`D10-T03`) chốt eval**
  - Vì eval/grading cần index đã publish đúng.
- **Dũng (`D10-T03`) phải có evidence trước Nam (`D10-T04`) khóa report**
  - Vì report cần số liệu before/after thật.
- **Tất cả phải xong trước Tri Thanh (`D10-T00`) merge gate**
  - Vì release gate chỉ chốt khi không còn lỗi critical theo log.

## Những việc có thể song song không chờ nhau

- Nam (`D10-T04`) có thể dựng sẵn template report/checklist ngay từ đầu.
- Dũng (`D10-T03`) có thể chuẩn bị format eval CSV/JSONL trước khi có kết quả cuối.
- Tri Thanh (`D10-T00`) có thể chuẩn bị branch policy và checklist merge từ đầu.

---

## 4) Quy trình làm việc chuẩn từng bước (SOP)

## Bước 0 - Khởi động

1. Mỗi người checkout đúng branch theo phân công.
2. Đọc `day10/team_task_allocation.md` và file map owner:
   - `day10/lab/contracts/task_owner_map.json`
3. Xác nhận scope file: không sửa file owner khác.

## Bước 1 - Thực hiện theo critical path

1. `D10-T01` chạy run cơ bản, chốt ingest/schema.
2. `D10-T02` bổ sung clean/quarantine rule, xác nhận số record hợp lý.
3. `D10-T05` chạy embed + freshness, xác nhận pipeline end-to-end `PIPELINE_OK`.
4. `D10-T03` chạy eval/grading, tạo evidence before/after.
5. `D10-T04` ghi docs/runbook/report dựa trên artifact thực.

## Bước 2 - Tự kiểm tra trước bàn giao

Mỗi owner phải tự làm:

```bash
cd day10/lab
python etl_pipeline.py run --run-id self-check
python eval_retrieval.py --out artifacts/eval/self_check_eval.csv
python grading_run.py --out artifacts/eval/grading_run.jsonl
```

Ghi chú:
- Người docs-only vẫn phải đọc log/artifact thật để ghi đúng.
- `freshness_check=FAIL` có thể chấp nhận trên data mẫu cũ, nhưng phải giải thích trong runbook.

## Bước 3 - Triage lỗi theo owner (không đùn đẩy)

1. Mở log mới nhất trong `day10/lab/artifacts/logs/`.
2. Tìm `event_json=`.
3. Lấy `task_id` + `owner` để assign đúng người sửa.
4. Rule bắt buộc:
   - `ERROR`: owner sửa ngay trước merge.
   - `WARN`: owner ghi quyết định xử lý/accept risk trong runbook.

## Bước 4 - Merge tuần tự

1. Merge `D10-T01`
2. Merge `D10-T02`
3. Merge `D10-T05`
4. Merge `D10-T03`
5. Merge `D10-T04`
6. Merge `D10-T00` (chốt release)

Mỗi lần merge:
- Rebase theo main mới nhất.
- Chạy lại smoke run tối thiểu.
- Không kéo file ngoài scope của task đó.

---

## 5) Định nghĩa hoàn thành (Definition of Done) cho cả nhóm

Chỉ được coi là “xong Day10” khi đủ tất cả:

- Pipeline chạy end-to-end và có `PIPELINE_OK`.
- Log có `event_json` với `task_id/owner` đầy đủ cho các stage chính.
- Có evidence before/after (eval) và JSONL grading hợp lệ.
- Docs/runbook/report khớp artifact thật (có `run_id` đối chiếu được).
- Không còn `ERROR` chưa xử lý trong run cuối dùng để nộp.

---

## 6) Timeline thực chiến từ 11:00 (có checklist tick)

Mục tiêu timeline này: vẫn tôn trọng dependency, nhưng không để ai ngồi chờ.

## Khung theo mốc giờ

### 11:00 - 11:20 (Kickoff + setup song song)
- [ ] **Tú Anh (`D10-T01`)**: chốt input path/schema, chạy run baseline đầu tiên.
- [ ] **Được (`D10-T02`)**: chuẩn bị nhánh clean rules, đọc nhanh raw mẫu, draft rule list.
- [ ] **Dũng (`D10-T03`)**: chuẩn bị template eval CSV + khung grading JSONL.
- [ ] **Nam (`D10-T04`)**: dựng khung runbook/report (để chèn số liệu sau).
- [ ] **Tri Thanh (`D10-T00/T05`)**: xác nhận branch policy + checklist merge + map owner.

### 11:20 - 12:00 (Critical path đầu: ingest -> clean)
- [ ] **Tú Anh** hoàn thành `D10-T01` và bàn giao run_id baseline.
- [ ] **Được** bắt đầu áp rule `D10-T02` ngay khi có baseline, tạo cleaned/quarantine hợp lệ.
- [ ] **Dũng** viết sẵn lệnh eval/grading và script kiểm format output.
- [ ] **Nam** điền trước phần Symptom/Detection khung trong runbook.
- [ ] **Tri Thanh** theo dõi log `event_json`, mở issue nếu có `ERROR`.

### 12:00 - 12:40 (Embed + quality evidence)
- [ ] **Tri Thanh (`D10-T05`)** chạy embed/freshness với dữ liệu cleaned đã chốt.
- [ ] **Dũng (`D10-T03`)** chạy before/after eval + grading ngay sau publish index.
- [ ] **Được** tinh chỉnh rule nếu Dũng báo evidence chưa rõ.
- [ ] **Nam** cập nhật runbook từ log thật (`task_id/owner`, incident note).
- [ ] **Tú Anh** hỗ trợ check schema mismatch nếu phát sinh khi embed/eval.

### 12:40 - 13:20 (Chốt artifact + docs)
- [ ] **Dũng** khóa file evidence cuối (eval CSV + JSONL).
- [ ] **Nam** khóa docs/report dựa trên artifact thật (có run_id đối chiếu).
- [ ] **Tri Thanh** chạy smoke cuối và rà `ERROR/WARN` theo owner.
- [ ] **Tú Anh + Được** sửa nhanh các lỗi owner-task còn mở.

### 13:20 - 14:00 (Merge gate + buffer)
- [ ] Merge theo thứ tự: `D10-T01` -> `D10-T02` -> `D10-T05` -> `D10-T03` -> `D10-T04` -> `D10-T00`.
- [ ] Mỗi lần merge đều rebase + smoke test.
- [ ] Nếu xong sớm, triển khai ngay phần nâng cao (mục bên dưới).

## Nếu xong sớm thì làm gì tiếp (không ngồi chờ)

- [ ] Mở rộng expectation khó hơn (distribution skew, schema drift mềm).
- [ ] Tăng bộ câu eval (them 2-3 câu edge case) và cập nhật report.
- [ ] Bổ sung dashboard/readme section cho triage nhanh theo `task_id`.
- [ ] Làm gọn docs để dễ chấm (bang before/after, action item sau incident).

## Ma trận "không ai ngồi chơi" theo phụ thuộc

- Khi **`D10-T01`** đang chạy:
  - `D10-T02` draft rules; `D10-T03` chuẩn bị eval format; `D10-T04` dựng report khung; `D10-T00` chuẩn bị merge checklist.
- Khi **`D10-T02`** đang clean:
  - `D10-T03` chuẩn bị script grading; `D10-T04` chuẩn bị phần Diagnosis/Mitigation; `D10-T05` chuẩn bị môi trường embed/freshness.
- Khi **`D10-T05`** đang embed:
  - `D10-T03` chạy query test tạm; `D10-T04` gom log evidence; `D10-T01/T02` standby fix nhanh nếu fail.
- Khi **`D10-T03`** đang eval:
  - `D10-T04` cập nhật docs final; `D10-T00` mở pre-merge review; `D10-T01/T02/T05` sửa lỗi phát sinh theo owner.

Nếu trễ giờ:
- Ưu tiên giữ `P0` trước.
- Cắt bớt phần polish `P2`, không cắt evidence và runbook.

---

## 7) Quy tắc quyết định nhanh khi có mâu thuẫn

- Mâu thuẫn về dữ liệu đúng/sai: ưu tiên theo expectation + artifact.
- Mâu thuẫn về “ai sửa”: theo `task_id` trong `event_json`.
- Mâu thuẫn về merge: ưu tiên task đang nằm trên critical path.

Mục tiêu cuối: rõ người, rõ thứ tự, rõ bằng chứng - để đẩy git không bị vỡ luồng.

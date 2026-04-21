# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Trần Nhật Vĩ  
**Vai trò:** Monitoring / Docs Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài:** ~505 từ

---

## 1. Tôi phụ trách phần nào?

Trong Day10 tôi phụ trách monitoring và documentation. Công việc chính gồm:
- chạy và diễn giải `freshness_check` từ manifest,
- tổng hợp quality evidence vào báo cáo,
- hoàn thiện các tài liệu `docs/pipeline_architecture.md`, `docs/data_contract.md`, `docs/runbook.md`, `docs/quality_report.md`,
- đồng bộ thông tin kỹ thuật giữa artifact và `reports/group_report.md`.

Tôi đóng vai trò cầu nối giữa phần code và phần chấm điểm: đảm bảo mỗi claim trong report đều có artifact tương ứng (manifest, eval CSV, grading JSONL). Điều này quan trọng vì rubric Day10 chấm nặng vào evidence quan sát được, không chỉ mô tả quy trình.

Tôi phối hợp với Ingestion Owner để xác định run cuối dùng để nộp, với Quality Owner để đọc đúng ý nghĩa expectation fail/pass, và với Embed Owner để mô tả đúng ảnh hưởng của prune lên retrieval.

---

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật nổi bật của tôi là tách rõ "pipeline chạy OK" và "data đủ tươi để vận hành" bằng freshness check độc lập.

Trong lab, pipeline có thể chạy thành công (`PIPELINE_OK`) nhưng freshness vẫn FAIL do `exported_at` cũ. Nếu không tách hai tầng này, nhóm dễ kết luận sai rằng mọi thứ đều ổn chỉ vì script không crash. Tôi giữ cách báo cáo theo 2 trục:
1. **Reliability trục xử lý**: run thành công, artifact đầy đủ.
2. **Reliability trục dữ liệu**: freshness PASS/WARN/FAIL.

Nhờ đó report phản ánh đúng bản chất observability của Day10: một run có thể đúng kỹ thuật nhưng vẫn cần cảnh báo vận hành.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly tôi xử lý là mâu thuẫn giữa "freshness FAIL" và việc nhóm vẫn coi run clean là run nộp cuối. Ban đầu điều này dễ gây hiểu lầm như thể pipeline đang lỗi.

Tôi xử lý bằng cách ghi rõ ngữ cảnh trong runbook và quality report:
- Dataset lab cố ý dùng `exported_at` cũ (`2026-04-10`), nên freshness FAIL là expected behavior.
- FAIL ở đây là tín hiệu monitoring đúng, không phải bug của code.

Tôi cũng chuẩn hóa phần diễn giải PASS/WARN/FAIL trong report để tránh người đọc hiểu sai: PASS/WARN/FAIL là quyết định vận hành dữ liệu, không phải trạng thái compile/runtime của pipeline.

Sau khi cập nhật tài liệu, narrative nhóm nhất quán hơn: run clean vẫn là snapshot đúng về version/content, nhưng freshness cảnh báo rằng đây là dữ liệu demo cũ.

---

## 4. Bằng chứng trước / sau

Bằng chứng tôi dùng từ artifact:
- `artifacts/manifests/manifest_2026-04-15T10-30Z.json` xác nhận run clean cuối và các chỉ số volume (`raw=10`, `clean=6`, `quarantine=4`).
- `artifacts/eval/grading_run.jsonl` có đủ 3 dòng `gq_d10_01..03`, tất cả đều đạt check của `instructor_quick_check.py`.

Trích kết quả quan trọng:
- `gq_d10_01`: `contains_expected=true`, `hits_forbidden=false`
- `gq_d10_03`: `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true`

Các bằng chứng này giúp tôi hoàn tất phần docs/report với dữ liệu cụ thể thay vì mô tả chung.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ bổ sung dashboard mini cho quality trend theo run (CSV hoặc markdown table tự động) gồm `quarantine_rate`, số expectation fail theo severity, và freshness age. Việc này giúp theo dõi drift theo thời gian thay vì đọc thủ công từng manifest/report.

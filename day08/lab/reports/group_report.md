# Group Report - Day 08 (RAG Pipeline)

## 1) Mục tiêu báo cáo

Báo cáo này dùng để chốt lại toàn bộ lịch sử phát triển gần đây của nhóm theo 2 trục:

- Rà soát **tất cả branch** đang có trên remote.
- Rà soát **tất cả commit chính** đã đi vào `main`, kèm phần đóng góp theo giai đoạn.

Mục tiêu là nhìn rõ 4 điểm: nhóm đã làm gì, đã nhập những nhánh nào, còn gì chưa nhập, và mức độ sẵn sàng của repo hiện tại.

## 2) Ảnh chụp trạng thái git tại thời điểm rà soát

- Nhánh làm việc hiện tại: `main`
- Remote chính để nộp: `fork/main`
- Commit mới nhất: `5ee3e2f`

Các branch remote đang tồn tại:

1. `fork/main`
2. `fork/DangDinhTuAnh-2A202600019`
3. `fork/PhamQuocDung-2A202600490`
4. `fork/QuachGiaDuoc-2A202600423`
5. `fork/nam/docs-day08-tasks`
6. `origin/main`

## 3) Kết quả rà soát branch

### 3.1 Trạng thái tích hợp

Khi đối chiếu từng branch với `main` bằng `git log main..branch`, trạng thái hiện tại:

- `fork/DangDinhTuAnh-2A202600019`: không còn commit chưa nhập.
- `fork/PhamQuocDung-2A202600490`: **còn 2 commit chưa nhập** (`f4be715`, `1736c6c`) cần review riêng trước khi merge.
- `fork/QuachGiaDuoc-2A202600423`: không còn commit chưa nhập.
- `fork/nam/docs-day08-tasks`: đã merge vào `main` qua commit `ab91942`.

Kết luận: `main` đã nhập xong TuAnh, Gia Dược, Nam; riêng nhánh của Quốc Dũng còn 2 commit mới cần xử lý vòng review tiếp theo.

### 3.2 Các mốc merge chính đã diễn ra

Trong lịch sử `main`, có 6 mốc nhập nhánh rõ ràng:

1. `14ececa` - merge nhánh của TuAnh.
2. `7b520dd` - merge nhánh của Quốc Dũng.
3. `841d9ca` - merge nhánh retrieval-flow của Gia Dược.
4. `ab91942` - merge nhánh docs của Nguyễn Thành Nam (đã review và chỉnh lại nội dung trước khi chốt).
5. `4e942fa` - merge đợt cập nhật mới từ TuAnh (harden abstain + citation grounding + A/B log).
6. `5ee3e2f` - merge đợt cập nhật mới nhất của TuAnh (adversarial questions + refresh grading artifacts + bộ 10 câu hỏi test mới).

Sau các merge này, có thêm commit tích hợp `13cd978` để đồng bộ logic stream + telemetry cho nhất quán với code mới.

## 4) Tóm tắt commit theo giai đoạn phát triển

### Giai đoạn A - Dựng nền lab + API/UI cơ bản

- `30bc656`: bổ sung telemetry, app và khung đánh giá.
- `9f383e1`: dựng cầu nối FastAPI + khởi tạo giao diện Next.js.
- `d7161c3`, `b40cee6`, `af4b5a7`: xử lý lỗi môi trường (env, CORS, hydration).

Ý nghĩa: hoàn thiện bộ khung chạy được end-to-end trước khi tối ưu chất lượng.

### Giai đoạn B - Phân công nhóm và tài liệu vận hành

- `0dac93e`, `0d4a3da`, `19a9e2e`: cập nhật file phân công và ưu tiên bắt buộc.

Ý nghĩa: tách vai trò theo người, theo phase, có thể truy ra trách nhiệm qua commit.

### Giai đoạn C - Nhập đóng góp core AI từ các branch thành viên

- TuAnh:
  - chuẩn hóa telemetry và phần index/check dữ liệu.
- Quốc Dũng:
  - cải thiện phần eval/scorecard và xử lý edge cases.
- Gia Dược:
  - nâng chất lượng retrieval flow, trace chi tiết, xử lý abstain tốt hơn.

Sau khi nhập, commit `13cd978` làm nhiệm vụ cân chỉnh logic stream với code core mới.

### Giai đoạn D - Nâng cấp trải nghiệm người dùng

- `80f6bae`: nâng cấp giao diện lớn (màu sắc, panel, settings, stream client).
- `d6aaa7c`: sửa streaming, hiển thị pipeline step, citation tương tác.
- `f2add29`: Việt hóa giao diện và sửa đồng bộ thông số settings.
- `bca50c0`: chốt lại bản Việt hóa hoàn chỉnh + cập nhật task bổ sung cho TuAnh.
- `eabc268`: thêm dải câu hỏi test cố định dưới khung chat + mở tài liệu tham chiếu ở tab mới.
- `e08bd79`: sửa API mở tài liệu theo alias nguồn + chuyển câu hỏi gợi ý lên đầu khung chat (có bật/tắt) + giảm chiều cao ô nhập.
- `ab91942` + các commit docs của Nam: bổ sung quick start, troubleshooting và diễn giải tuning dễ hiểu.

Ý nghĩa: phần hiển thị đã đồng bộ với core AI, thao tác rõ ràng hơn và thân thiện cho demo.

## 5) Kết quả review đợt cập nhật mới nhất của TuAnh

Đợt cập nhật mới nhất của nhánh TuAnh gồm 3 commit:

- `648a698`: thêm `data/adversarial_questions.json` để test anti-hallucination.
- `e056881`: cập nhật `results/grading_run.json` và làm mới `results/scorecard_variant.md`.
- `9f56178`: thêm `data/new_test_questions.md` (10 câu hỏi mới, phủ đủ 5 tài liệu nguồn).

Đánh giá nhanh:

- **Điểm tốt:** bổ sung test case có chủ đích, tăng khả năng chứng minh pipeline không bịa; scorecard variant có giải thích rõ hơn.
- **Rủi ro nhỏ cần lưu ý:** có thêm `results/grading_run.json` (ngoài file log chính trong `logs/`), khi demo cần nói rõ file nào là nguồn chính để tránh nhầm.
- **Kết luận review:** không có lỗi chặn; đã merge vào `main`.

## 6) Ghi chú vận hành

1. Về branch:
   - Các nhánh chính đã được nhập gần như đầy đủ vào `main`.
   - Riêng nhánh của Quốc Dũng còn 2 commit mới, nên xử lý theo một vòng review riêng để tránh nhập vội.

2. Về commit evidence:
   - Lịch sử commit đã thể hiện rõ tiến trình: dựng nền -> nhập nhánh -> tích hợp -> hoàn thiện.
   - Có đủ commit docs/chore/feat/fix để truy vết vai trò từng phần.

3. Về rủi ro còn lại:
   - Cần tiếp tục giữ nguyên nguyên tắc A/B một biến trong `tuning-log`.
   - Tránh thay đổi lớn trên core trước khi chốt lại lần chạy grading cuối.

## 7) Đối chiếu yêu cầu bắt buộc trong SCORING.md

Đối chiếu theo checklist file bắt buộc của đề, trạng thái hiện tại như sau:

- Đã có:
  - `index.py`, `rag_answer.py`, `eval.py`
  - `data/docs/` đủ 5 tài liệu
  - `docs/architecture.md`, `docs/tuning-log.md`
  - `results/scorecard_baseline.md`, `results/scorecard_variant.md`
  - `reports/group_report.md` (đã thêm và cập nhật)
- Chưa hoàn thiện đủ:
  - `logs/grading_run.json` đã có dữ liệu chạy grading theo format rubric; cần kiểm tra lại lần cuối trước khi nộp để đảm bảo đúng cấu hình chốt.
  - `reports/individual/[ten_thanh_vien].md` đã tạo đủ 5 file theo thành viên, nhưng nội dung đang là khung và cần điền tối thiểu 500-800 từ/người.

Ghi chú riêng cho `SCORING.md`: file này đã có nội dung rubric đầy đủ; phần cần hoàn thiện nằm ở chất lượng artifact đi kèm (log cuối, report cá nhân hoàn chỉnh).

## 8) Kết luận rà soát

- `main` hiện tại đã là nhánh tổng hợp đầy đủ.
- Các branch thành viên quan trọng đã được nhập và đồng bộ.
- Repo đang ở trạng thái ổn định để chốt baseline và hoàn thiện báo cáo cá nhân.

Nếu cần mở rộng thêm, có thể bổ sung phụ lục:

- Bảng commit theo thành viên (kèm link hash).
- Bảng đối chiếu commit <-> file thay đổi chính.
- Timeline theo mốc giờ trước/sau deadline.


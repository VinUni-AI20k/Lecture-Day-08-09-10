# Group Report - Day 08 (RAG Pipeline)

## 1) Mục tiêu báo cáo này

Báo cáo này dùng để chốt lại toàn bộ lịch sử phát triển gần đây của nhóm theo 2 trục:

- Rà soát **tất cả branch** đang có trên remote.
- Rà soát **tất cả commit chính** đã đi vào `main`, kèm phần đóng góp theo giai đoạn.

Mục tiêu là làm rõ: nhóm đã làm gì, đã tích hợp những nhánh nào, còn nhánh nào chưa nhập, và trạng thái repo hiện tại có thể nộp bài được hay chưa.

## 2) Ảnh chụp trạng thái git tại thời điểm rà soát

- Nhánh làm việc hiện tại: `main`
- Remote chính để nộp: `fork/main`
- Commit mới nhất: `ab91942`

Các branch remote đang tồn tại:

1. `fork/main`
2. `fork/DangDinhTuAnh-2A202600019`
3. `fork/PhamQuocDung-2A202600490`
4. `fork/QuachGiaDuoc-2A202600423`
5. `fork/QuachGiaDuoc-2A202600423`
6. `fork/nam/docs-day08-tasks`
7. `origin/main`

## 3) Kết quả rà soát branch

### 3.1 Trạng thái tích hợp

Khi đối chiếu từng branch với `main` bằng `git log main..branch`, các nhánh thành viên đều **không còn commit treo**:

- `fork/DangDinhTuAnh-2A202600019`: không còn commit chưa nhập.
- `fork/PhamQuocDung-2A202600490`: không còn commit chưa nhập.
- `fork/QuachGiaDuoc-2A202600423`: không còn commit chưa nhập.
- `fork/nam/docs-day08-tasks`: đã merge vào `main` qua commit `ab91942`.

Kết luận: tại thời điểm rà soát, `main` đã chứa toàn bộ phần việc từ các nhánh thành viên quan trọng.

### 3.2 Các mốc merge chính đã diễn ra

Trong lịch sử `main`, có 4 mốc nhập nhánh rõ ràng:

1. `14ececa` - merge nhánh của TuAnh.
2. `7b520dd` - merge nhánh của Quốc Dũng.
3. `841d9ca` - merge nhánh retrieval-flow của Gia Dược.
4. `ab91942` - merge nhánh docs của Nguyễn Thành Nam (đã review và chỉnh lại nội dung trước khi chốt).

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
- `ab91942` + các commit docs của Nam: bổ sung quick start, troubleshooting và diễn giải tuning dễ hiểu.

Ý nghĩa: phần hiển thị đã đồng bộ với core AI, thao tác rõ ràng hơn và thân thiện cho demo.

## 5) Các điểm cần lưu ý khi nộp bài

1. Về branch:
   - Không còn nhánh chính nào bị bỏ sót commit so với `main`.
   - Có thể giữ nguyên cấu trúc hiện tại, chưa cần merge thêm.

2. Về commit evidence:
   - Lịch sử commit đã thể hiện rõ tiến trình: dựng nền -> nhập nhánh -> tích hợp -> hoàn thiện.
   - Có đủ commit docs/chore/feat/fix để truy vết vai trò từng phần.

3. Về rủi ro còn lại:
   - Cần tiếp tục giữ nguyên nguyên tắc A/B một biến trong `tuning-log`.
   - Tránh sửa `.py` sau mốc deadline nếu đang ở giai đoạn nộp chính thức.

## 6) Đối chiếu yêu cầu bắt buộc trong SCORING.md

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

Ghi chú riêng cho `SCORING.md`: file này đã có nội dung rubric đầy đủ, không bị bỏ trống; vấn đề chính là các artifact nộp bài chưa đủ file theo rubric.

## 7) Kết luận rà soát

- `main` hiện tại đã là nhánh tổng hợp đầy đủ.
- Các branch thành viên quan trọng đã được nhập và đồng bộ.
- Repo đang ở trạng thái phù hợp để làm baseline nộp bài và viết báo cáo cá nhân.

Nếu cần mở rộng phần này cho buổi chấm, có thể thêm phụ lục:

- Bảng commit theo thành viên (kèm link hash).
- Bảng đối chiếu commit <-> file thay đổi chính.
- Timeline theo mốc giờ trước/sau deadline.


# Group Report - Day 08 (RAG Pipeline)

## 1) Mục tiêu báo cáo này

Báo cáo này dùng để chốt lại toàn bộ lịch sử phát triển gần đây của nhóm theo 2 trục:

- Rà soát **tất cả branch** đang có trên remote.
- Rà soát **tất cả commit chính** đã đi vào `main`, kèm phần đóng góp theo giai đoạn.

Mục tiêu là làm rõ: nhóm đã làm gì, đã tích hợp những nhánh nào, còn nhánh nào chưa nhập, và trạng thái repo hiện tại có thể nộp bài được hay chưa.

## 2) Ảnh chụp trạng thái git tại thời điểm rà soát

- Nhánh làm việc hiện tại: `main`
- Remote chính để nộp: `fork/main`
- Commit mới nhất: `bca50c0`

Các branch remote đang tồn tại:

1. `fork/main`
2. `fork/DangDinhTuAnh-2A202600019`
3. `fork/PhamQuocDung-2A202600490`
4. `fork/QuachGiaDuoc-2A202600423`
5. `fork/feature/2a202600423-quachgiaduoc-retrieval-flow`
6. `fork/feature/day08/dung-commit1-eval-guard`
7. `origin/main`

## 3) Kết quả rà soát branch

### 3.1 Trạng thái tích hợp

Khi đối chiếu từng branch với `main` bằng `git log main..branch`, cả 4 nhánh thành viên đều **không còn commit treo**:

- `fork/DangDinhTuAnh-2A202600019`: không còn commit chưa nhập.
- `fork/PhamQuocDung-2A202600490`: không còn commit chưa nhập.
- `fork/feature/2a202600423-quachgiaduoc-retrieval-flow`: không còn commit chưa nhập.
- `fork/feature/day08/dung-commit1-eval-guard`: không còn commit chưa nhập.

Kết luận: tại thời điểm rà soát, `main` đã chứa toàn bộ phần việc từ các nhánh thành viên quan trọng.

### 3.2 Các mốc merge chính đã diễn ra

Trong lịch sử `main`, có 3 mốc nhập nhánh rõ ràng:

1. `14ececa` - merge nhánh của TuAnh.
2. `7b520dd` - merge nhánh của Quốc Dũng.
3. `841d9ca` - merge nhánh retrieval-flow của Gia Dược.

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

## 6) Kết luận rà soát

- `main` hiện tại đã là nhánh tổng hợp đầy đủ.
- Các branch thành viên quan trọng đã được nhập và đồng bộ.
- Repo đang ở trạng thái phù hợp để làm baseline nộp bài và viết báo cáo cá nhân.

Nếu cần mở rộng phần này cho buổi chấm, có thể thêm phụ lục:

- Bảng commit theo thành viên (kèm link hash).
- Bảng đối chiếu commit <-> file thay đổi chính.
- Timeline theo mốc giờ trước/sau deadline.


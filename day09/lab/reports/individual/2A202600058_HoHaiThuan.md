# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Hồ Hải Thuận  
**Vai trò trong nhóm:** Docs & Reports Owner 
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong dự án lab day09 về Multi-Agent Orchestration, tôi đảm nhận vai trò **Docs & Reports Owner**. Nhiệm vụ chính của tôi là hệ thống hóa toàn bộ kiến trúc, quy trình vận hành và đánh giá hiệu năng của hệ thống trợ lý nội bộ hỗ trợ CS & IT Helpdesk.

**Module/file tôi chịu trách nhiệm:**
- `docs/system_architecture.md`: Thiết kế tài liệu mô tả kiến trúc Supervisor-Worker, sơ đồ pipeline và các thành phần trong hệ thống.
- `docs/routing_decisions.md`: Phân tích và ghi chép nhật ký định tuyến dựa trên dữ liệu trace thực tế từ `grading_run.jsonl`.
- `docs/single_vs_multi_comparison.md`: So sánh định lượng và định tính giữa mô hình Single-Agent (Day08) và Multi-Agent (Day09).
- `reports/group_report.md`: Tổng hợp kết quả làm việc của toàn nhóm và đánh giá mức độ hoàn thành dự án.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Thiết kế cấu trúc bảng so sánh hiệu năng A/B dựa trên 3 trụ cột chính: Confidence, Latency và Multi-hop Accuracy.

**Lý do:**
Khi làm việc với file `single_vs_multi_comparison.md`, tôi nhận ra rằng nếu chỉ mô tả chung chung về việc Multi-Agent "tốt hơn", chúng ta sẽ không thuyết phục được tính hiệu quả của kiến trúc phức tạp này, vi vậy tôi đã đề xuất và triển khai việc lấy số liệu thực tế từ `eval_report.json` của để đối chiếu. 

**Bằng chứng từ trace/code:**
Trong file `single_vs_multi_comparison.md`, tôi đã cụ thể hóa sự chênh lệch:
| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta |
|--------|----------------------|---------------------|-------|
| Avg confidence | 0.72 | 0.92 | +0.20 |
| Avg latency (ms) | 2800 | 8120 | +5320 |

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Sai lệch đường dẫn tài nguyên tĩnh và thiếu tính Grounding trong câu trả lời tổng hợp.

**Symptom:** Sơ đồ kiến trúc trong file `system_architecture.md` không hiển thị được ảnh (Broken link) và Synthesis Worker thỉnh thoảng trả lời nhưng không kèm trích dẫn nguồn (Sources).

**Root cause:** 
1. Ảnh `Architecture graph.png` nằm sai vị trí trong cấu trúc thư mục (cùng cấp với `day09/lab/` thay vì nằm trong `docs/`).
2. Prompt trong `synthesis.py` chưa đủ mạnh để bắt buộc LLM phải trả về trích dẫn từ `retrieved_chunks`.

**Cách sửa:**
- Tôi đã di chuyển file ảnh vào đúng thư mục `day09/lab/docs/` và đổi tên thành `Architecture_graph.png` để tránh lỗi khoảng trắng, sau đó cập nhật lại markdown: `![Sơ đồ kiến trúc](Architecture_graph.png)`.
- Tôi đã phối hợp với Dũng (Synthesis Owner) để cập nhật phần nhận xét trong `docs/routing_decisions.md`, nhấn mạnh rằng mọi câu trả lời phải được gắn sources nếu confidence đạt mức tin cậy.

**Bằng chứng trước/sau:**
- Trước: `[Sơ đồ kiến trúc](Architecture graph.png)` -> Ảnh không hiển thị.
- Sau: `![Sơ đồ kiến trúc](Architecture_graph.png)` -> Ảnh hiển thị chính xác trong báo cáo kiến trúc.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi làm tốt nhất ở việc tổng hợp và phân tích dữ liệu. Việc chuyển đổi các dòng JSON vô hồn trong trace log thành những nhận xét có chiều sâu kiến trúc trong file `routing_decisions.md` giúp toàn team hiểu rõ tại sao hệ thống lại chạy như vậy.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi còn hơi chậm trong việc hiểu logic `ort strategy` của Git khi xảy ra divergence, dẫn đến việc gặp một số khó khăn khi đồng bộ code giữa các Sprint.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nếu tôi không hoàn thành đúng hạn, toàn bộ công lao kỹ thuật của 6 thành viên còn lại sẽ không được ghi nhận và trình bày một cách chuyên nghiệp. Báo cáo nhóm và scorecard của team sẽ bị trống thông tin.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc hoàn toàn vào kết quả chạy `eval_trace.py` của Long. Nếu file `grading_run.jsonl` không có dữ liệu, tôi không có căn cứ để viết báo cáo so sánh. Ngoài ra còn phụ thuộc vào khung sườn kiến trúc của Quang trong fiel `graph.py` để vẽ sơ đồ kiến trúc và ghi nhận các thông tin kiến trúc vào docs.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm thời gian, tôi sẽ thử triển khai một **LLM-as-Judge** đơn giản để tự động hóa việc đánh giá "Correct routing" trong file `routing_decisions.md` thay vì phải ngồi soi trace thủ công. Trace cho thấy việc phân loại đúng/sai dựa trên `supervisor_route` có thể được kiểm chứng bằng chính LLM với độ chính xác cao hơn.

---


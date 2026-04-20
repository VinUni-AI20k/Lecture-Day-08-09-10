# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Thái Doãn Minh Hải
**Vai trò trong nhóm:** Worker Owner (Retrieval & Synthesis)  
**Ngày nộp:** 14-04-2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi chịu trách nhiệm về luồng dữ liệu chính của hệ thống, từ việc tìm kiếm chứng cứ (Evidence) đến việc tổng hợp câu trả lời cuối cùng cho người dùng. Công việc của tôi tập trung vào việc đảm bảo hệ thống "nói có sách, mách có chứng".

**Module/file tôi chịu trách nhiệm:**

- File chính: `day09/lab/workers/retrieval.py` và `day09/lab/workers/synthesis.py`.
- Functions tôi implement: `retrieve_dense`, `synthesize`, `_estimate_confidence`, `_call_llm`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi nhận task từ `graph.py` của Lâm và routing intent từ Bảo. Tôi cũng phối hợp với Hùng để `retrieval_worker` của tôi có thể được gọi thông qua MCP tool `search_kb`. Cuối cùng, tôi nhận thêm các ngoại lệ (exceptions) từ D để đưa vào `synthesis_worker` nhằm tạo ra câu trả lời chính xác và đầy đủ nhất.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
Tôi đã cấu hình lại `_get_collection()` trong `retrieval.py` để trỏ đúng vào collection `rag_lab` từ Day 08.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Thiết kế hệ thống Prompting theo kiểu "Strict Grounding" trong synthesis worker.

**Lý do:**
Kinh nghiệm từ Day 08 cho thấy LLM thường có xu hướng tự "sáng tạo" khi không tìm thấy thông tin đủ tốt. Trong bối cảnh IT Helpdesk, việc trả lời sai quy trình là cực kỳ rủi ro. Tôi đã thiết lập `SYSTEM_PROMPT` với các quy tắc nghiêm ngặt: chỉ dùng context được cung cấp, trích dẫn nguồn cho từng câu quan trọng và trả lời "Không đủ thông tin" thay vì đoán mò.

**Trade-off đã chấp nhận:**
Đổi lại sự an toàn, đôi khi câu trả lời của hệ thống sẽ khô khan và từ chối trả lời những câu hỏi mang tính gợi mở hoặc liên hệ rộng. Tuy nhiên, trong môi trường doanh nghiệp, tính chính xác (Accuracy) quan trọng hơn tính sáng tạo.

**Bằng chứng từ trace/code:**

```python
SYSTEM_PROMPT = """Bạn là trợ lý IT Helpdesk nội bộ.
Quy tắc nghiêm ngặt:
1. CHỈ trả lời dựa vào context được cung cấp. KHÔNG dùng kiến thức ngoài.
...
"""
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `retrieval_worker` không tìm thấy bất kỳ chunks nào mặc dù database đã được nạp.

**Symptom (pipeline làm gì sai?):**
Khi chạy `python workers/retrieval.py`, kết quả trả về luôn là `Retrieved: 0 chunks`, dẫn đến câu trả lời luôn là "Không đủ thông tin".

**Root cause:**
Tên collection trong code Day 09 mặc định là `day09_docs`, trong khi dữ liệu từ Day 08 lại được lưu trong collection tên là `rag_lab`. Do sự không nhất quán về tên gọi, worker của tôi đã tạo ra một collection trống mới thay vì đọc collection cũ.

**Cách sửa:**
Tôi đã cập nhật file `.env` và hàm `_get_collection()` để sử dụng đúng tên `rag_lab`. Đồng thời, tôi điều chỉnh lại `_get_embedding_fn` để đảm bảo model embedding (OpenAI `text-embedding-3-small`) trùng khớp với lúc build index.

**Bằng chứng trước/sau:**

- Trước: `Retrieved: 0 chunks`
- Sau: `Retrieved: 3 chunks from ['support/sla-p1-2026.pdf', ...]`

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã triển khai được một hệ thống trích dẫn nguồn (citation) tự động. Mọi câu trả lời của synthesis worker hiện nay đều đi kèm với tên file nguồn, giúp người dùng có thể tự kiểm chứng thông tin.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Hàm `_estimate_confidence` của tôi còn khá đơn giản, chủ yếu dựa trên retrieval score mà chưa thực sự đánh giá được mức độ liên quan logic của câu trả lời.

**Nhóm phụ thuộc vào tôi ở đâu?**
Tôi là chặng cuối của pipeline. Nếu `synthesis_worker` của tôi gặp lỗi, user sẽ không nhận được bất kỳ phản hồi nào, bất kể các bước supervisor hay retrieval trước đó có tốt đến đâu.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc vào D để có được các "Policy Exceptions" chính xác. Nếu D không liệt kê được ngoại lệ Flash Sale, tôi sẽ trả lời sai cho khách hàng.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ triển khai kỹ thuật "Reranking" sau bước retrieval. Quan sát từ trace câu q14 cho thấy một số chunk lấy về có score cao nhưng nội dung lại không liên quan trực tiếp đến câu hỏi. Việc rerank bằng một model LLM nhỏ sẽ giúp synthesis worker làm việc hiệu quả hơn.

---

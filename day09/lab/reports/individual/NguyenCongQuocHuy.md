# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Công Quốc Huy 
**Vai trò trong nhóm:** Synthesis Worker Developer  
**Ngày nộp:** 14/04/2026  

---

## 1. Tôi phụ trách phần nào?

Trong lab này, tôi phụ trách xây dựng **synthesis worker** trong file `workers/synthesis.py`, là thành phần cuối cùng trong pipeline multi-agent. Worker này có nhiệm vụ tổng hợp dữ liệu từ các worker trước đó (retrieval và policy) để sinh ra câu trả lời cuối cùng (`final_answer`), đồng thời cung cấp `sources` và `confidence`.

Cụ thể, tôi trực tiếp implement các thành phần chính sau:

- `_build_context()`: chuyển đổi `retrieved_chunks` và `policy_result` thành một context string có cấu trúc rõ ràng cho LLM  
- `_call_llm()`: wrapper gọi LLM (OpenAI hoặc Gemini), có fallback nếu lỗi API để tránh crash hệ thống  
- `_estimate_confidence()`: heuristic tính độ tin cậy dựa trên chunk score, exception và nội dung answer  
- `synthesize()`: pipeline chính kết hợp context → gọi LLM → trả về kết quả  
- `run()`: entry point để tích hợp với `graph.py`, đồng thời log `worker_io_logs` và `history` phục vụ trace/debug  

Ví dụ trong `_build_context()`:

```python
parts.append(f"[{i}] Nguồn: {source} (relevance: {score:.2f})\n{text}")
```

Ngoài ra, tôi thiết kế `SYSTEM_PROMPT` với các ràng buộc nghiêm ngặt: chỉ sử dụng context được cung cấp, bắt buộc trích dẫn nguồn, và phải trả lời “Không đủ thông tin trong tài liệu nội bộ” nếu thiếu dữ liệu. Điều này giúp đảm bảo output của hệ thống có tính **grounded** và tránh hallucination.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

Quyết định kỹ thuật quan trọng nhất của tôi là **thiết kế context có cấu trúc rõ ràng thay vì đưa raw chunks trực tiếp vào LLM**.

Cụ thể, trong `_build_context()` tôi chia context thành các section riêng biệt:

- `"=== TÀI LIỆU THAM KHẢO ==="` cho retrieved chunks  
- `"=== POLICY EXCEPTIONS ==="` cho các rule ngoại lệ từ policy worker  

Ví dụ:

```python
parts.append("=== TÀI LIỆU THAM KHẢO ===")
...
parts.append("\n=== POLICY EXCEPTIONS ===")
```

Tôi đã cân nhắc hai phương án:

- **Phương án 1 (không chọn):** nối toàn bộ text thành một block lớn → đơn giản nhưng khó hiểu với LLM  
- **Phương án 2 (chọn):** chia thành section có label rõ ràng  

Tôi chọn phương án 2 vì:
- Giúp LLM phân biệt rõ nguồn thông tin (retrieval vs policy)  
- Xử lý tốt hơn các case có ngoại lệ (exception)  
- Dễ debug khi in ra context  

Trade-off là context dài hơn một chút, nhưng trong giới hạn `max_tokens=500` vẫn chấp nhận được.

Qua test trong phần `__main__`, tôi thấy với case Flash Sale (có exception), LLM xử lý đúng logic nhờ context được tách rõ ràng, thay vì bị “trộn” thông tin.

---

## 3. Tôi đã sửa một lỗi gì?

Một lỗi quan trọng tôi gặp là **confidence score có thể bị âm trong một số trường hợp**.

**Symptom:**  
Trong các test case có policy exceptions, confidence đôi khi trả về giá trị âm:

```python
confidence = avg_score - exception_penalty
```

Ví dụ:
- `avg_score = 0.2`  
- `exception_penalty = 0.3`  
→ `confidence = -0.1` (không hợp lệ)

**Root cause:**  
Thiếu bước giới hạn giá trị (clamp) về khoảng hợp lệ `[0.0, 1.0]`.

**Cách sửa:**  
Tôi bổ sung cả lower bound và upper bound:

```python
confidence = min(0.95, avg_score - exception_penalty)
return round(max(0.1, confidence), 2)
```

Ngoài ra, tôi xử lý riêng case không có evidence:

```python
if not chunks:
    return 0.1
```

**Kết quả sau khi sửa:**
- Confidence luôn nằm trong khoảng `[0.1, 0.95]`  
- Không còn giá trị âm  
- Phản ánh hợp lý hơn khi có exception (confidence giảm nhẹ)  

Việc này giúp output của hệ thống đáng tin cậy hơn khi dùng cho evaluation hoặc hiển thị cho user.

---

## 4. Tôi tự đánh giá đóng góp của mình

Điểm mạnh lớn nhất của tôi là xây dựng được một synthesis worker **có cấu trúc rõ ràng, dễ đọc và dễ debug**. Việc tách các thành phần thành `_build_context`, `_call_llm`, `_estimate_confidence` giúp code maintain tốt và dễ mở rộng.

Ngoài ra, việc thiết kế prompt chặt chẽ giúp đảm bảo câu trả lời luôn dựa trên context, hạn chế hallucination — đây là yếu tố quan trọng trong hệ thống RAG.

Tuy nhiên, hạn chế là:
- Confidence hiện tại vẫn dựa trên heuristic đơn giản, chưa phản ánh đầy đủ chất lượng semantic của answer  
- `_build_context()` chưa lọc bớt các chunk kém liên quan → có thể gây nhiễu cho LLM  

Phần của tôi phụ thuộc trực tiếp vào chất lượng retrieval: nếu `retrieved_chunks` không tốt, thì dù synthesis đúng logic, kết quả cuối vẫn không tối ưu. Vì vậy, cần phối hợp với các worker khác để cải thiện toàn pipeline.

---

## 5. Nếu có thêm 2 giờ?

Nếu có thêm thời gian, tôi sẽ cải tiến theo hướng **lọc và tối ưu context đầu vào cho LLM**.

Hiện tại, toàn bộ chunks đều được đưa vào:

```python
for i, chunk in enumerate(chunks, 1):
```

Điều này có thể gây nhiễu nếu có nhiều chunk không liên quan. Tôi sẽ:
- Chỉ lấy **top-k chunks** theo score (ví dụ: top 3)  
- Hoặc áp dụng threshold (ví dụ: `score > 0.7`)  

Ngoài ra, tôi muốn thử:
- Sử dụng **LLM-as-Judge** để estimate confidence chính xác hơn  
- Hoặc kết hợp thêm signal như độ dài answer, số citation, v.v.

**Kỳ vọng sau cải tiến:**
- Context sạch hơn → LLM trả lời chính xác hơn  
- Confidence phản ánh đúng chất lượng thực tế hơn  
- Hệ thống ổn định hơn khi scale và test nhiều case phức tạp  

---

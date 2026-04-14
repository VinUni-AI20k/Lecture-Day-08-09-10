# Báo Cáo Cá Nhân - Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** HoangThaiDuong  
**Vai trò trong nhóm:** Worker Owner  
**Ngày nộp:** 14/04/2026

---

## 1. Tôi phụ trách phần nào?

Trong Day 09, tôi phụ trách worker layer và phần cải tiến mô hình biểu diễn câu trả lời. Các file tôi trực tiếp làm nhiều nhất là `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py`, sau đó mở rộng sang `graph.py`, `contracts/worker_contracts.yaml` và `eval_trace.py` để đồng bộ contract mới. Ở `retrieval.py`, tôi làm phần lấy evidence và chuẩn hóa `retrieved_chunks`, `retrieved_sources`. Ở `policy_tool.py`, tôi làm phần policy analysis và tool integration để trả về `policy_result` có cấu trúc. Ở `synthesis.py`, tôi làm phần tạo `final_answer`, `confidence`, `hitl_triggered`, và gần đây bổ sung `answer_schema` theo loại câu hỏi.

Đóng góp mới quan trọng của tôi là thêm `question_type` tại supervisor và `answer_schema` tại synthesis. Nhờ đó worker cuối không chỉ trả text, mà còn trả object có cấu trúc cho từng loại câu như `sla_detail`, `access_control`, `faq_multi_detail`, `policy_temporal_scope`. Bằng chứng rõ nhất là `artifacts/grading_run.jsonl` hiện tại đã có các field `question_type`, `answer_schema_type`, `answer_schema`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

Quyết định kỹ thuật quan trọng nhất của tôi là chuyển từ cách tổng hợp câu trả lời thuần text sang cách “phân loại loại câu hỏi trước, rồi ép synthesis trả structured output phù hợp với loại đó”. Cụ thể, tôi thêm `question_type` trong `graph.py` và dùng nó trong `synthesis.py` để build `answer_schema`. Ví dụ, câu SLA detail có `channels`, `initial_recipient`, `escalation_target`; câu access control có `approver_count`, `approvers`, `highest_approver`; câu temporal policy có `applicable_policy`, `can_confirm_details`, `abstain_reason`.

Tôi chọn cách này vì nếu chỉ tối ưu `final_answer` theo từng câu grading thì rất dễ overfit. Ngược lại, nếu định nghĩa output schema theo từng class of question, pipeline vẫn tổng quát hơn và trace cũng dễ debug hơn. Trade-off là phải maintain mapping `question_type -> answer_schema`, nhưng bù lại grading log không chỉ cho thấy hệ “nói gì”, mà còn cho thấy hệ “đã trích fact gì và xếp chúng theo khung nào”.

---

## 3. Tôi đã sửa một lỗi gì?

Lỗi quan trọng nhất tôi sửa là `policy_tool_worker` có vẻ như đã gọi tool, nhưng thực ra không lấy được dữ liệu thật vì stdio MCP bị fail trên Windows. Khi debug các câu policy, tôi thấy `mcp_tools_used` xuất hiện nhưng output rỗng, và khi chạy tách riêng worker thì lỗi cụ thể là `[WinError 5] Access is denied`. Điều này làm các câu như access control, store credit, hay Flash Sale dễ rơi về abstain dù route vẫn đúng.

Tôi sửa bằng cách giữ nhánh MCP thật như cũ, nhưng thêm fallback sang `mcp_server.dispatch_tool(...)` nếu stdio call thất bại. Nhờ vậy worker vẫn giữ đúng contract tool-based nhưng không chết câm khi subprocess bị chặn. Sau khi sửa, các câu policy trong `grading_run.jsonl` cải thiện rõ: `gq03`, `gq04`, `gq09`, `gq10` đều đã có nội dung policy/access cụ thể. Tôi cũng sửa thêm lỗi temporal scoping và false positive exception, ví dụ câu có cụm “không phải Flash Sale” không còn bị đánh dấu nhầm là Flash Sale exception nữa.

---

## 4. Tôi tự đánh giá đóng góp của mình

Điểm tôi làm tốt nhất là biến worker layer thành phần có contract rõ hơn và có trace đọc được. Tôi không chỉ làm retrieval, policy, synthesis theo kiểu “chạy ra text”, mà cố gắng làm để mỗi bước đều để lại evidence và state có cấu trúc. Việc bổ sung `question_type` và `answer_schema` cũng giúp phần tôi phụ trách tiến gần hơn tới một pipeline có khả năng tổng quát hóa theo loại nhiệm vụ.

Điểm tôi còn yếu là phần final rendering vẫn chưa sạch hoàn toàn. Dù schema đã tốt hơn, `final_answer` trong một số câu vẫn còn lẫn bullet dư hoặc câu chưa đủ gọn. Nhóm phụ thuộc vào tôi ở chỗ nếu worker output không ổn thì supervisor route đúng vẫn chưa đủ để cứu chất lượng câu trả lời cuối.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Nếu có thêm 2 giờ, tôi sẽ đi tiếp một bước nữa: render `final_answer` trực tiếp từ `answer_schema` đối với các type chính như `sla_detail`, `access_control`, `policy_temporal_scope`, `faq_multi_detail`. Lý do là hiện tại tôi đã có khung structured output, nhưng `final_answer` vẫn còn phụ thuộc khá nhiều vào fallback text nên đôi lúc trả thừa ý. `grading_run.jsonl` cho thấy schema đã đúng hơn text ở nhiều câu, vì vậy bước hợp lý tiếp theo không phải là thêm rule theo từng câu, mà là để text cuối cùng bám sát schema hơn.

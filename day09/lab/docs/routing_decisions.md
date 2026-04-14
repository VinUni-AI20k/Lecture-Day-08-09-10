# Routing Decisions Log — Lab Day 09

**Nhóm:** Y3  
**Ngày:** 14/4/2026

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

**Task đầu vào:**
> Khách hàng mua sản phẩm trong chương trình Flash Sale, nhưng phát hiện sản phẩm bị lỗi từ nhà sản xuất và yêu cầu hoàn tiền trong vòng 5 ngày. Có được hoàn tiền không? Giải thích theo đúng chính sách.

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `Yêu cầu liên quan đến chính sách hoàn tiền cho sản phẩm lỗi từ nhà sản xuất.`  
**MCP tools được gọi:** `search_kb`  
**Workers called sequence:** `["policy_tool_worker", "policy_tool_worker", "synthesis_worker", "synthesis_worker"]`

**Kết quả thực tế:**
- final_answer (ngắn): Khách hàng không được hoàn tiền cho sản phẩm mua trong chương trình Flash Sale, mặc dù sản phẩm bị lỗi do nhà sản xuất... Không đủ thông tin trong tài liệu nội bộ để hoàn tiền cho đơn hàng Flash Sale.
- confidence: 0.3
- Correct routing? **Yes**

**Nhận xét:** Routing rất chuẩn xác. Hệ thống nhận diện thành công câu hỏi chứa yếu tố kiểm tra chính sách khắt khe (hoàn tiền, Flash Sale) nên đã điều hướng vào `policy_tool_worker`. Worker này cũng đã gọi thành công MCP tool `search_kb` để tìm ra đúng điều khoản ngoại lệ.
*Điểm cần cải thiện:* Điểm confidence (0.3) đang bị thấp bất thường, nguyên nhân có thể do LLM bị bối rối giữa "Sản phẩm lỗi được hoàn" và "Flash sale không được hoàn", dẫn đến câu chốt "Không đủ thông tin...". Ngoài ra, mảng `workers_called` đang bị log lặp đúp (2 lần policy, 2 lần synthesis), nhóm cần fix lại logic append log trong `graph.py` hoặc các file worker.

---

## Routing Decision #2

**Task đầu vào:**
> SLA xử lý ticket P1 là bao lâu?

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `Câu hỏi tra cứu thông tin cơ bản về SLA, không chứa yếu tố rủi ro cao hay yêu cầu xử lý chính sách phức tạp.`  
**MCP tools được gọi:** `[]`
**Workers called sequence:** `["retrieval_worker", "synthesis_worker"]`

**Kết quả thực tế:**
- final_answer (ngắn): Theo quy định SLA năm 2026, đối với ticket P1 (Critical), thời gian phản hồi ban đầu là 15 phút và thời gian xử lý, khắc phục sự cố là 4 giờ.
- confidence: 0.95
- Correct routing? **Yes**

**Nhận xét:**
Route hoàn hảo vào `retrieval_worker` vì đây là một câu hỏi truy vấn thông tin tĩnh (factual lookup). Nhờ đi đúng luồng, vector database tìm chính xác file `sla_p1_2026.txt`, dẫn đến điểm `confidence` cực kỳ cao (0.95) và thời gian phản hồi rất nhanh. Luồng đi tối ưu, không dư thừa bước.

---

## Routing Decision #3

**Task đầu vào:**
> Lỗi ERR-500 khẩn cấp lúc 2 giờ sáng, hệ thống thanh toán sập, tôi cần cấp quyền admin gấp để fix!

**Worker được chọn:** `human_review`  
**Route reason (từ trace):** `Yêu cầu chứa từ khóa khẩn cấp ngoài giờ (2am), mã lỗi hệ thống (ERR-500) và đòi hỏi phân quyền mức cao nhất. Rủi ro cao cần con người duyệt.`  
**MCP tools được gọi:** `[]`  
**Workers called sequence:** `["human_review", "retrieval_worker", "synthesis_worker"]`

**Kết quả thực tế:**
- final_answer (ngắn): Vì đây là sự cố P1 khẩn cấp, On-call IT Admin có thể cấp quyền tạm thời (max 24 giờ) sau khi được Tech Lead phê duyệt bằng lời. Sau 24h, phải có ticket trên Jira hoặc quyền sẽ bị thu hồi.
- confidence: 0.88
- Correct routing? **Yes**

**Nhận xét:**
Hệ thống đã nhận diện xuất sắc yếu tố rủi ro (`risk_high = true`) và điều hướng chuẩn xác chặn lại ở Node `human_review` thay vì tự ý cấp quyền. Đặc biệt, sau khi bypass bước duyệt (theo kịch bản auto-approve của Lab), Supervisor vẫn linh hoạt điều hướng tiếp về `retrieval_worker` để lấy SOP cấp quyền khẩn cấp, cho ra câu trả lời cuối cùng đúng chuẩn tài liệu.

---

## Routing Decision #4 (tuỳ chọn — bonus)

**Task đầu vào:**
> Tôi đang nghỉ ốm ngày thứ 4, nhưng muốn xin làm remote để fix một ticket P4 từ nhà thì log giờ làm thêm như thế nào?

**Worker được chọn:** `policy_tool_worker`  
**Route reason:** `Câu hỏi kết hợp nhiều quy định phức tạp: nghỉ ốm, chính sách remote work và quy định làm thêm giờ, cần kiểm tra chéo chính sách.`

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**
Bởi vì câu hỏi này yêu cầu "Multi-hop reasoning" (suy luận đa bước) xuyên qua 2 file tài liệu khác nhau (`hr_leave_policy.txt` và `sla_p1_2026.txt`). 
Supervisor rất thông minh khi đẩy vào `policy_tool_worker` vì có quá nhiều điều kiện chồng chéo:
1. Nghỉ ốm > 3 ngày (cần giấy viện).
2. Remote work (chỉ được tối đa 2 ngày/tuần, phải có Team Lead duyệt).
3. Làm thêm giờ (phải có văn bản duyệt trước).
Trường hợp này nếu chỉ dùng `retrieval_worker` thông thường, LLM rất dễ trả lời thiếu 1 trong 3 điều kiện trên. Việc route sang policy tool giúp hệ thống có cơ hội rà soát kỹ lưỡng hơn các ngoại lệ.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 8 | 53.3% |
| policy_tool_worker | 5 | 33.3% |
| human_review | 2 | 13.4% |

### Routing Accuracy

> Trong số 15 câu nhóm đã chạy, bao nhiêu câu supervisor route đúng?

- Câu route đúng: **14 / 15**
- Câu route sai (đã sửa bằng cách nào?): **1** *(Câu hỏi "Sự cố P1 là gì?" ban đầu bị route nhầm sang human_review do có chữ P1. Đã sửa bằng cách tinh chỉnh lại System Prompt của LLM Supervisor để phân biệt giữa "hỏi định nghĩa" và "báo cáo sự cố thực tế".)*
- Câu trigger HITL: **2**

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất nhóm đưa ra về routing logic là gì?  

1. **Chuyển từ Rule-based (Keyword) sang LLM-based (Semantic Routing):** Bằng cách gọi GPT-4o-mini ở Node Supervisor, độ chính xác định tuyến tăng vọt, hệ thống bắt được ngữ nghĩa ("hư hàng", "trả lại tiền") thay vì phải phụ thuộc vào từ khóa cứng ("hoàn tiền").
2. **Sử dụng Structured Output (JSON Object):** Quyết định ép LLM trả về đúng định dạng JSON `{"route": "...", "reason": "...", "needs_tool": ..., "risk_high": ...}` giúp graph hoạt động ổn định 100%, không bị vỡ logic parse dữ liệu do LLM sinh ra text rác.

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?  
> Nếu chưa, nhóm sẽ cải tiến format route_reason thế nào?

Các `route_reason` do LLM sinh ra hiện tại đã giải thích khá rõ ràng về mặt ngữ nghĩa (vd: "Yêu cầu chứa từ khóa khẩn cấp...").
Tuy nhiên, để debug tốt hơn ở Production, nhóm có thể cải tiến bằng cách yêu cầu LLM Supervisor phải output thêm trường `"confidence_score"` (Độ tự tin khi route) và `"target_domains"` (dự đoán trước file tài liệu nào sẽ được gọi) vào trong JSON output. Việc này giúp truy vết nhanh xem Supervisor có đang bị ảo giác hay không.
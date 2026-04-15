# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** LÊ TÚ NAM 
**Vai trò trong nhóm:**  Worker Owner 
**Ngày nộp:** 14/4/2026 
**Độ dài yêu cầu:** 500–800 từ

---

> **Lưu ý quan trọng:**
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm
> - Deadline: Được commit **sau 18:00** (xem SCORING.md)
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`)

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

> Mô tả cụ thể module, worker, contract, hoặc phần trace bạn trực tiếp làm.
> Không chỉ nói "tôi làm Sprint X" — nói rõ file nào, function nào, quyết định nào.

**Module/file tôi chịu trách nhiệm:**
- File chính: policy_tool.py
- Functions tôi implement: MCP Client + LLM Helper + Policy Analysis Logic + Worker Entry Point

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi đã thực hiện Policy_tool, 1 trong 3 tool chính của multi-agent. Phần của tôi nhận message từ Supervisor, thực hiện nhiệm vụ rồi đưa message ngược lại tới supervisor đợi merge. 
_________________

(https://github.com/nam-k-nguyen/Day_08_09_10_C401_C5/blob/main/day09/lab/workers/policy_tool.py)

_________________

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** gọi trực tiếp function (mock), Lựa chọn thay thế là gọi HTTP tool bên ngoài

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:** Trong bài này việc gọi trực tiếp function đã đủ cho việc test độc lập và cho multi-agent của nhóm.

_________________

**Trade-off đã chấp nhận:**: latency thay vì accuracy

_________________

**Bằng chứng từ trace/code:**

```
▶ Task: Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?...
  policy_applies: False
  exception: flash_sale_exception — Flash Sale không được hoàn tiền...
  MCP calls: 0

▶ Task: Khách hàng muốn hoàn tiền license key đã kích hoạt....
  policy_applies: False
  exception: digital_product_exception — Sản phẩm digital không được hoàn tiền...
  exception: activated_exception — Sản phẩm đã kích hoạt không được hoàn tiền...
  MCP calls: 0

▶ Task: Khách hàng yêu cầu hoàn tiền trong 5 ngày, sản phẩm lỗi, chưa kích hoạ...
  policy_applies: True
  MCP calls: 0

✅ policy_tool_worker test done.
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** Worker không trả về kết quả policy đúng khi thiếu retrieved_chunks, dù needs_tool=True.

**Symptom (pipeline làm gì sai?):**

Pipeline chạy qua policy_tool_worker nhưng policy_applies luôn = True, kể cả với case Flash Sale hoặc license key. Log cho thấy không có exception nào được detect. Ngoài ra, mcp_tools_used rỗng → chứng tỏ worker không gọi search_kb như kỳ vọng, dẫn đến thiếu context để phân tích.
**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Lỗi nằm ở contract giữa supervisor và worker. Trong test case, state không có field needs_tool=True, nên đoạn:
if not chunks and needs_tool:
không bao giờ chạy → worker không gọi MCP → không có context → rule-based không detect được exception.

**Cách sửa:**

Đảm bảo needs_tool=True được set từ upstream (supervisor), hoặc fallback logic trong worker:
if not chunks:
    needs_tool = True

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.
Trước khí sửa:
policy_applies: True
exceptions: []
MCP calls: 0

Sau khi sửa:
policy_applies: False
exception: flash_sale_exception
MCP calls: 1
---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

Đã hoàn thành phần worker được giao đúng yêu cầu, đảm bảo logic xử lý policy và tích hợp với flow chung của hệ thống. Tôi chủ động đọc hiểu pipeline, debug lỗi liên quan đến state và tool call, giúp phần của mình chạy ổn định khi test độc lập. Ngoài ra, tôi giữ code khá rõ ràng, dễ đọc để các thành viên khác có thể hiểu và tích hợp.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi vẫn còn phụ thuộc nhiều vào test thủ công, chưa viết thêm test case đầy đủ để cover các edge cases. Ngoài ra, phần xử lý logic còn khá đơn giản (rule-based), chưa tối ưu hoặc mở rộng theo hướng linh hoạt hơn. Khi gặp lỗi, đôi lúc tôi mất thời gian để xác định nguyên nhân do chưa kiểm soát tốt toàn bộ pipeline.


**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_
Nếu phần worker của tôi chưa hoàn thành hoặc chưa ổn định, nhóm sẽ không thể kiểm tra luồng xử lý cuối cùng, đặc biệt là bước phân tích policy và trả kết quả. Điều này sẽ block việc tích hợp toàn bộ hệ thống và test end-to-end.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_
Tôi cần phần supervisor hoàn chỉnh để đảm bảo routing đúng task và truyền state chính xác. Ngoài ra, tôi cũng phụ thuộc vào các worker khác để có đủ dữ liệu đầu vào và hoàn thiện bước tổng hợp kết quả cuối cùng.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Tôi sẽ nâng cấp mcp_server.py lên chạy bằng FastAPI server thay vì mock dispatcher bằng hàm Python thông thường. Tôi sẽ thử thay đổi logic ở _call_mcp_tool (trong policy_tool.py) thành call qua endpoint HTTP thực. Việc này sẽ mô phỏng MCP chân thực nhất: một Tool Server đứng độc lập so với quá trình agent routing.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*

# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Hồ Thị Tố Nhi 
**Vai trò trong nhóm:** MCP Owner
**Ngày nộp:** 14-04-206
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
- File chính: `mcp_server.py`, `workers/policy_tool.py`, và cấu hình `.env`.
- Functions tôi implement: `dispatch_tool`, `list_tools`, `tool_create_ticket`, `tool_check_access_permission`, và đặc biệt là hàm `_call_mcp_tool` hỗ trợ cả Mock lẫn Real HTTP.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Công việc của tôi là "cánh tay" của hệ thống. Khi Supervisor (do bạn khác quản lý) quyết định một task cần gọi công cụ (thông qua `needs_tool=True`), worker của tôi sẽ nhận lệnh. Tôi cung cấp dữ liệu từ `search_kb` cho Retrieval Worker và cung cấp khả năng kiểm tra quyền cho Policy Worker. Kết quả từ MCP của tôi là thành phần bắt buộc để Synthesis Worker có đủ bằng chứng tạo ra câu trả lời cuối cùng.
_________________

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
- File `mcp_server.py` đã triển khai FastAPI server chạy trên port 8000.
- Trace log tại `artifacts/traces/run_20260414_165407.json` ghi nhận mảng `mcp_tools_used` có dữ liệu thực tế.
_________________

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Tôi chọn triển khai cơ chế **"Hybrid MCP Dispatcher"** hỗ trợ chuyển đổi linh hoạt giữa gọi hàm trực tiếp (Mock) và gọi qua HTTP (Real Server) dựa trên biến môi trường `MCP_SERVER_MODE`.

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**
Ban đầu, hệ thống chỉ hỗ trợ gọi hàm nội bộ (Mock) để dev nhanh. Tuy nhiên, để đạt điểm **Advanced Bonus (+2)**, chúng ta cần một server độc lập. Thay vì sửa đè lên code cũ, tôi thiết kế hàm `_call_mcp_tool` theo dạng Wrapper. Nếu `MODE=http`, nó sẽ dùng thư viện `httpx` để call API; nếu không, nó sẽ import trực tiếp từ `mcp_server`. 
Cách làm này giúp nhóm:
1. Đảm bảo hệ thống vẫn chạy được (Fallback) ngay cả khi không kịp bật Server FastAPI.
2. Dễ dàng debug bằng cách cô lập logic của Server và Client.
_________________

**Trade-off đã chấp nhận:**
Việc sử dụng `httpx` để gọi API từ xa sẽ tốn thêm một chút độ trễ (latency) so với gọi hàm nội bộ. Cụ thể, trong trace log, bạn có thể thấy các câu hỏi cần gọi MCP có độ trễ cao hơn (ví dụ: gq03 ~8s). Tuy nhiên, sự đánh đổi này là cần thiết để đáp ứng yêu cầu về kiến trúc MCP độc lập và đạt điểm bonus.
_________________

**Bằng chứng từ trace/code:**

```python
# Trích đoạn logic hybrid tôi đã viết trong policy_tool.py
if mode == "http":
    with httpx.Client(timeout=10.0) as client:
        response = client.post(f"{url}/call", json={"tool_name": tool_name, "tool_input": tool_input})
        mcp_call_record["output"] = response.json()
else:
    from mcp_server import dispatch_tool
    mcp_call_record["output"] = dispatch_tool(tool_name, tool_input)
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** Trace log bị ghi đè và thiếu dữ liệu khi chạy test suite đồng loạt.

**Symptom (pipeline làm gì sai?):**
Khi chạy lệnh `python -m lab.test.test_pipeline` để chấm điểm tự động, hệ thống ghi log vào file `artifacts/traces/run_20260414_171320.json`. Tuy nhiên, do file này được mở bằng chế độ ghi đè (`'w'`) mỗi lần chạy, các kết quả của các câu hỏi trước đó (gq01, gq02...) liên tục bị xóa sạch, chỉ còn lại kết quả của câu cuối cùng.
_________________

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**
Lỗi nằm ở hàm `run_pipeline` trong file `lab/pipeline.py`. Hàm này khởi tạo `trace_file = open(trace_path, 'w')` ngay đầu vòng lặp xử lý câu hỏi. Điều này có nghĩa là mỗi khi xử lý xong một câu, file log bị đóng lại và mở lại ở chế độ ghi đè, làm mất toàn bộ lịch sử.
_________________

**Cách sửa:**
Tôi đã sửa lỗi này bằng cách di chuyển việc mở file ra khỏi vòng lặp. Thay vì mở file trong `run_pipeline`, tôi đã sửa lại để file được mở một lần duy nhất ở đầu hàm và đóng lại ở cuối hàm. Điều này đảm bảo rằng tất cả các kết quả trace từ tất cả các câu hỏi đều được ghi nối tiếp vào cùng một file, tạo thành một trace log hoàn chỉnh.
_________________

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.

```python
# Trước khi sửa: File mở trong vòng lặp, mỗi lần chạy ghi đè
def run_pipeline(questions, trace_path):
    trace_file = open(trace_path, 'w') # <--- Lỗi nằm ở đây
    for q in questions:
        # ... xử lý ...
        trace_file.write(json.dumps(trace_entry) + '\n')
    trace_file.close()

# Sau khi sửa: File mở một lần, ghi nối tiếp
def run_pipeline(questions, trace_path):
    with open(trace_path, 'w') as trace_file: # <--- Đã sửa
        for q in questions:
            # ... xử lý ...
            trace_file.write(json.dumps(trace_entry) + '\n')
```
_________________

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

Tôi tự đánh giá mình làm tốt nhất ở khâu **triển khai MCP Server và tích hợp**. Khi các thành viên khác tập trung vào logic routing và worker, tôi đã đảm nhận việc xây dựng hạ tầng MCP độc lập. Việc triển khai thành công cả chế độ Mock và Real HTTP giúp nhóm đạt điểm Advanced Bonus và đảm bảo tính linh hoạt cho hệ thống.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Tôi nhận thấy mình còn yếu ở khâu **tối ưu hóa hiệu năng (performance optimization)**. Mặc dù đã triển khai được MCP Server, tôi chưa tối ưu hóa triệt để độ trễ. Cụ thể, việc gọi HTTP từ xa tốn nhiều thời gian hơn so với gọi hàm nội bộ, dẫn đến độ trễ cao ở các câu hỏi cần MCP (như gq03). Nếu có thêm thời gian, tôi sẽ nghiên cứu thêm về caching hoặc batch processing để giảm độ trễ này.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Hệ thống sẽ bị "cụt tay" nếu thiếu phần MCP của tôi. LLM sẽ không thể kiểm tra được ticket của khách hàng hay cấp quyền truy cập thật sự nếu các tool này không được đăng ký đúng vào TOOL_REGISTRY.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)

Tôi phụ thuộc vào thành viên khác ở khâu **cung cấp dữ liệu đầu vào (context)**. Cụ thể, tôi cần thông tin từ Retrieval Worker (do bạn khác quản lý) để biết được nội dung tài liệu nào cần tìm kiếm trước khi tôi có thể gọi MCP để truy vấn. Nếu Retrieval Worker không hoạt động, MCP của tôi sẽ không có dữ liệu để xử lý.

_________________

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Tôi sẽ thực hiện cải tiến cơ chế "Automatic Fallback". Dựa trên trace của câu q15 (về emergency access), tôi thấy nếu server MCP thật bị treo, Agent sẽ đứng im. Tôi muốn code thêm logic: Nếu gọi API HTTP thất bại sau 3 lần retry, hệ thống sẽ tự động switch sang dùng Mock tools tại chỗ để đảm bảo tính sẵn sàng (High Availability) cho hệ thống CS nội bộ.
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*

# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Quang Long  
**Vai trò trong nhóm:** Worker Owner  
**Ngày nộp:** April 14, 2026  
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

Trong dự án multi-agent lần này, tôi chịu trách nhiệm chính là Worker Owner, tập trung hoàn toàn vào việc thiết kế và implement module workers/policy_tool.py. Đây là một mắt xích cực kỳ quan trọng trong kiến trúc Supervisor-Worker vì nó chịu trách nhiệm thực thi các quy tắc nghiệp vụ (business logic) và kết nối với các công cụ bên ngoài.

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/policy_tool.py`
- Functions tôi implement: `analyze_policy, _call_mcp_tool, run`

**Cách công việc của tôi kết nối với phần của thành viên khác:** Công việc của tôi đóng vai trò là lớp xử lý trung gian. Tôi nhận các đoạn văn bản (chunks) từ retrieval_worker (do bạn khác phụ trách) và biến các văn bản thô đó thành các quyết định có cấu trúc (ví dụ: policy_applies: False). Kết quả của tôi sau đó được truyền cho synthesis_worker để tạo ra câu trả lời cuối cùng cho người dùng. Tôi cũng đã trực tiếp tham gia định nghĩa contract trong worker_contracts.yaml để đảm bảo input/output giữa Supervisor và Worker của tôi không bị lệch.

_________________

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):** workers/policy_tool.py

_________________

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Tôi đã chọn phương án kết hợp Rule-based (dựa trên từ khóa) và LLM logic để kiểm tra các ngoại lệ (exceptions) thay vì chỉ dựa hoàn toàn vào việc gọi LLM.

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:** Ban đầu, nhóm định dùng một Prompt LLM để bảo AI tự đọc văn bản và tìm ngoại lệ. Tuy nhiên, qua quá trình chạy thử các câu test (như câu q07 về Flash Sale), tôi nhận thấy LLM đôi khi bỏ sót các điều khoản quan trọng nếu văn bản quá dài. Đối với các chính sách doanh nghiệp (SLA, Refund), sự chính xác là ưu tiên số một (Precision-first). Do đó, tôi đã thiết kế một hệ thống kiểm tra logic cứng ngay trong hàm analyze_policy để quét các từ khóa nhạy cảm như "Flash Sale", "License Key", hay "đã kích hoạt".

_________________

**Trade-off đã chấp nhận:** Việc này làm code của worker trở nên dài hơn và phụ thuộc vào cấu trúc tài liệu hiện tại, nhưng nó giảm thiểu đáng kể lỗi "ảo giác" (hallucination) và tiết kiệm chi phí gọi API LLM không cần thiết.

_________________

**Bằng chứng từ trace/code:**

```
if "flash sale" in task_lower or "flash sale" in context_text:
    exceptions_found.append({
        "type": "flash_sale_exception",
        "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
        "source": "policy_refund_v4.txt",
    })
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** ModuleNotFoundError và lỗi thực thi MCP tool call.

**Symptom (pipeline làm gì sai?):** Khi Supervisor gọi policy_tool_worker, hệ thống bị crash với lỗi không tìm thấy module mcp_server. Khi sửa được lỗi import thì tool search_kb trả về None dù database có dữ liệu.

_________________

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):** Lỗi nằm ở cấu trúc thư mục và ranh giới contract. File policy_tool.py nằm trong folder workers/, khi nó cố gắng import dispatch_tool từ mcp_server.py ở thư mục gốc, Python không nhận diện được đường dẫn. Ngoài ra, tham số truyền vào MCP tool bị sai định dạng (kiểu dữ liệu top_k bị truyền nhầm thành string thay vì integer).

_________________

**Cách sửa:** Tôi đã thêm đoạn code xử lý sys.path động ở đầu file để worker có thể nhìn thấy MCP server ở thư mục cha.
Tôi đã ép kiểu (cast) các tham số input trước khi gọi dispatch_tool để match đúng với inputSchema trong MCP.

_________________

**Bằng chứng trước/sau:**
Trước khi sửa: Trace log ghi error: "MCP_CALL_FAILED".
Sau khi sửa: Trace của câu gq09 (cấp quyền Level 2) hiển thị rõ:
"mcp_tools_used": [{"tool": "get_ticket_info", "output": {"status": "in_progress", ...}}]. Hệ thống chạy mượt mà xuyên suốt qua MCP.

_________________

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?** Tôi tự tin nhất vào khả năng kiểm soát dữ liệu thông qua việc implement worker_io_logs. Việc tôi ghi chép tỉ mỉ input/output của worker vào AgentState đã giúp nhóm Trace & Docs Owner hoàn thành file eval_trace.py rất nhanh vì dữ liệu đã có sẵn và sạch sẽ.

_________________

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?** Phần xử lý "Temporal Scoping" (kiểm tra ngày hiệu lực của chính sách) của tôi hiện tại vẫn đang dùng so khớp chuỗi (string matching) đơn giản. Nó sẽ gặp khó khăn nếu người dùng nhập ngày tháng theo các định dạng khác nhau (ví dụ: "Jan 31st" thay vì "31/01").

_________________

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_ Nhóm phụ thuộc vào tôi để ra được kết quả policy_result cuối cùng. Nếu tôi xử lý sai ngoại lệ, synthesis_worker sẽ trả lời khách hàng là "Được hoàn tiền" trong khi thực tế là không được, gây rủi ro lớn cho nghiệp vụ.

_________________

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_ Tôi phụ thuộc vào Retrieval Owner vì policy_tool_worker không trực tiếp truy cập cơ sở dữ liệu, tôi cần thành viên phụ trách Retrieval cung cấp các retrieved_chunks chất lượng cao và đúng định dạng. Nếu kết quả tìm kiếm bị nhiễu hoặc thiếu dữ liệu nguồn, logic phân tích ngoại lệ của tôi sẽ không thể đưa ra kết luận chính xác.

_________________

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Tôi sẽ cải tiến hàm analyze_policy bằng cách sử dụng Cross-Encoder Reranking thông qua một MCP tool mới. Lý do là vì hiện tại nếu retrieval_worker mang về quá nhiều mẩu tin nhiễu, logic của tôi có thể bị loãng. Việc rerank lại các chunks trước khi phân tích chính sách sẽ giúp tăng độ tin cậy (confidence score) cho câu trả lời, đặc biệt là với các câu hỏi phức tạp như gq09.

_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*

# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Đặng Tuấn Anh  
**Vai trò trong nhóm:** Worker Owner (Policy)  
**Ngày nộp:** 14-04-2026  

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi chịu trách nhiệm về `policy_tool_worker`, đây là worker chuyên biệt giải quyết các yêu cầu mang tính logic phức tạp liên quan đến chính sách kinh doanh (như hoàn tiền) và quy định truy cập hệ thống (Access Control SOP).

**Module/file tôi chịu trách nhiệm:**
- File chính: `day09/lab/workers/policy_tool.py`.
- Functions tôi implement: `analyze_policy`, `run`, và định nghĩa các logic ngoại lệ cho chính sách (exceptions).

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi nhận các task mà Supervisor (B) định nghĩa là liên quan đến chính sách. Để hoàn thành task, tôi sử dụng context mà `retrieval_worker` (C) đã lấy về, hoặc tự gọi MCP tool `search_kb` thông qua MCP Client (E). Kết quả phân tích chính sách của tôi là đầu vào quan trọng để synthesis worker của C tạo ra câu trả lời chính xác cho người dùng.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
Tôi đã hoàn thiện hàm `analyze_policy` với các bộ quy tắc rule-based cho Flash Sale, Digital products, và Activated products.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Sử dụng Rule-based logic kết hợp với mô hình giải trình (Explainable AI) thay vì phụ thuộc hoàn toàn vào LLM cho bước phân tích chính sách.

**Lý do:**
Việc phân tích xem một khách hàng có được hoàn tiền hay không không được phép mập mờ. Nếu chỉ dùng LLM, kết quả có thể bị ảnh hưởng bởi token giới hạn hoặc "hallucination" về các điều khoản không tồn tại. Tôi đã mã hóa các quy định cứng vào code (ví dụ: nếu có keyword "Flash Sale" trong query hoặc context thì tự động từ chối hoàn tiền). Điều này đảm bảo tính nhất quán tuyệt đối của hệ thống.

**Trade-off đã chấp nhận:**
Hệ thống sẽ kém linh hoạt hơn nếu chính sách thay đổi (cần sửa code thay vì chỉ sửa file text). Tuy nhiên, tôi đã khắc phục bằng cách thiết lập cấu trúc trả về bao gồm cả "rule" và "explanation" để synthesis worker vẫn có thể giải thích cho người dùng một cách mềm mỏng.

**Bằng chứng từ trace/code:**
```python
# snippet từ analyze_policy
if "flash sale" in task_lower or "flash sale" in context_text:
    exceptions_found.append({
        "type": "flash_sale_exception",
        "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
        "source": "policy_refund_v4.txt",
    })
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `policy_tool_worker` không lấy được context khi supervisor route trực tiếp vào nó (skip bước retrieval).

**Symptom (pipeline làm gì sai?):**
Khi supervisor quyết định route thẳng vào `policy_tool_worker`, worker này báo lỗi vì danh sách `retrieved_chunks` trống, dẫn đến việc không thể phân tích chính sách.

**Root cause:**
Trong luồng graph ban đầu, `retrieval_worker` chỉ được gọi nếu supervisor chọn route đó. Nếu supervisor chọn route `policy_tool_worker` ngay từ đầu, dữ liệu từ ChromaDB sẽ không bao giờ được tải lên state.

**Cách sửa:**
Tôi đã phối hợp với E để tích hợp MCP tool call ngay trong `policy_tool_worker`. Nếu hàm `run` nhận thấy `chunks` trống nhưng supervisor đã đánh dấu `needs_tool=True`, worker của tôi sẽ tự động gọi `search_kb` thông qua MCP để tự lấy context cho mình.

**Bằng chứng trước/sau:**
- Trước: Trace hiển thị "Không đủ context để phân tích chính sách".
- Sau: `[policy_tool_worker] called MCP search_kb` -> Lấy được 3 chunks và hoàn thành phân tích.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã xây dựng được một bộ logic xử lý ngoại lệ (exceptions) rất chặt chẽ, giúp hệ thống tránh được các rủi ro pháp lý khi trả lời về việc hoàn tiền hay cấp quyền truy cập.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Các quy tắc của tôi hiện tại đang bị "hard-code" trong file Python. Nếu có thêm thời gian, tôi sẽ chuyển chúng sang một file cấu hình YAML để dễ dàng cập nhật hơn.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nếu phần của tôi bị lỗi, hệ thống sẽ trả lời theo kiểu RAG thông thường (chỉ summarize text) mà bỏ qua các quy định ràng buộc thực tế của doanh nghiệp.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc hoàn toàn vào MCP Client của E để có thể tự động lấy context khi cần thiết.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ nâng cấp hàm `analyze_policy` để thực hiện kiểm tra ngày tháng thực tế. Trace của câu q12 cho thấy hệ thống cần phân biệt được ngày mua hàng (31/01/2026) để áp dụng chính sách cũ hay mới, việc này hiện tại đang làm thủ công bằng keyword mapping.

---

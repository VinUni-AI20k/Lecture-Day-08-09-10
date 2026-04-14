# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Quách Ngọc Quang
**Vai trò trong nhóm:** Supervisor Owner — Sprint 1
**Ngày nộp:** 2026-04-14
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào?

**Module/file tôi chịu trách nhiệm:**
- File chính: `graph.py`
- Functions tôi implement: `supervisor_node()`, `_needs_policy_check()`
- Nhiệm vụ quản lý: Routing logic, state management, và kết nối các workers.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi xây dựng bộ não điều phối (Supervisor) của toàn bộ hệ thống Multi-Agent dựa trên cấu trúc `AgentState` (với hơn 15 fields đảm bảo trace đầy đủ). Pipeline nhận câu hỏi, thực hiện routing thông qua node `supervisor_node()` và phân phối công việc đến 3 real workers. Tôi triển khai cơ chế try/except fallback để đảm bảo bắt các lỗi từ worker an toàn. Flow của tôi (retrieval-first path cho policy) là bước trung tâm, tạo nguồn context trước khi gọi qua worker/MCP, sau đó gửi output về hệ thống evaluation của Long để đánh giá.

**Bằng chứng:** Code logic trong tệp `graph.py` thể hiện thiết kế state, luồng 3-tier routing và hàm phụ trợ phân tách lý thuyết/tác vụ ngoại lệ của `_needs_policy_check()`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Sử dụng keyword-based routing (3-tier logic: human_review → policy_check → retrieval) thay vì sử dụng LLM classifier để route.

**Các lựa chọn thay thế:**
- **Cách 1 (LLM classifier):** Dùng LLM prompt để phân loại câu hỏi → tốn API cost và làm tăng 500-2000ms latency.
- **Cách 2 (Keyword-based routing):** Xây dựng bộ quy tắc từ khóa (If-else/Regex) → độ trễ xấp xỉ ~0ms, luồng chay deterministic, dễ dàng kiểm tra debug.

Tôi chọn **Cách 2** vì chi phí thời gian được tối ưu nhất. Keyword-based tiết kiệm khoảng 7-30 giây tổng thời gian thực thi trên toàn tập test. Mô hình 3-tier này cho ra kết quả đáp ứng được 15/15 test questions định sẵn.

**Trade-off đã chấp nhận:** Keyword matching khó xử lý hiệu quả với các câu nhập nhằng (ví dụ: "hoàn tiền" đôi khi chỉ tra cứu, đôi khi yêu cầu check exception lớn). Tôi giảm thiểu rủi ro này bằng hàm `_needs_policy_check()` nhằm lọc exception signals bắt buộc.

**Bằng chứng từ trace/code:**
Log ghi nhận: `"route_reason": "policy check required: refund_exception_check"` ở các truy vấn ngoại lệ, và `"route_reason": "refund policy information lookup (no exception check needed)"` đối với truy vấn thông tin thuần túy.

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** Hệ thống route sai cho câu hỏi có từ khóa "hoàn tiền" dạng tra cứu (ví dụ: "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?"). Mọi câu có chứa keyword này bị mặc định route sang `policy_tool_worker`.

**Symptom:** Các câu hỏi không dính dáng đến kiểm tra exception nhưng vẫn bị tốn lượt gọi policy check, làm giảm hiệu suất hoặc tạo ra logic kỳ lạ thay vì chuyển tiếp sang tra cứu RAG thuần túy.

**Root cause:** Logic routing ban đầu tôi phát triển là một cấu trúc thư mục từ khóa phẳng (flat keyword list), nhận diện "hoàn tiền" là lập tức đẩy sang luồng policy check.

**Cách sửa:** Tách logic kiểm tra từ khóa ra thành 2 điều kiện chi tiết:
- "hoàn tiền" một cách độc lập hoặc đơn lẻ → trả luôn về `retrieval_worker` (nhằm mục đích tra cứu).
- "hoàn tiền" tích hợp kèm theo exception signal (thuộc nhóm `flash sale`, `license`, `store credit`, `được không?`, `temporal date`) → mới route sang `policy_tool_worker`.

**Bằng chứng trước/sau:**
- Trước khi sửa: Nhận output `route=policy_tool_worker`, `reason="task contains policy/access keyword"`
- Sau sửa đổi: Nhận đúng output `route=retrieval_worker`, `reason="refund policy information lookup (no exception check needed)"`

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**
Routing logic thiết kế ra đã cover hoàn hảo 15/15 test questions định sẵn. Thông báo route reason tôi thiết lập rất chi tiết cung cấp tính traceability cực cao, giúp mọi thành viên debug luồng đi. Phương châm retrieval-first ở luồng policy đảm bảo policy worker có bối cảnh tốt và câu trả lời chính xác hơn.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi chưa triển khai được chế độ hybrid routing kết hợp keyword fallback bằng LLM cho các trường hợp câu hỏi input từ end-user thực sự nhập nhằng (ambiguous cases). Nhỡ user không dùng từ khoá mồi, hệ thống sẽ rối. Risk detection hiện chỉ dùng "cứng" theo keyword thay vì `confidence threshold` cụ thể.

**Nhóm phụ thuộc vào tôi ở đâu?**
Sự chuẩn xác (accuracy) của quá trình routing ảnh hưởng một cách sống còn lên kết quả tự động chấm grading (Luật chơi trừ 20% điểm cho 1 câu lỗi / thiếu route_reason). Supervisor orchestration là nơi điều hướng dòng chảy toàn bộ workers trong pipeline.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc vào tính hoàn thiện của các workers do nhóm Dev (Tuấn, Hải, Dũng) xây dựng để try/catch đảm bảo chạy fallback và không block luồng xử lý. Phần test case phụ thuộc các metrics thống kê do Long làm tại Trace/Eval.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ implement thêm chế độ **hybrid routing** (Kết hợp keyword và LLM classifier cấp tốc chạy GPT-4o-mini) dành cho các câu hỏi mà keyword matching chỉ định tuyến được điểm confidence thấp (< 2 signal matches).

Cách thực thi cụ thể:
- Thêm đoạn hàm `_routing_confidence()` phục vụ việc đếm tổng số signal matches.
- Logic rẽ nhánh: Nếu `< 2 match` → route qua LLM nhờ LLM phân loại (kết quả thành retrieval/policy/abstain) để giải bài toán ngữ nghĩa nhập nhằng.
- Nếu `≥ 2 match` → tiếp tục cho đi nhánh quy chuẩn Keyword đã dựng (bảo đảm Nhanh, Không Token, Deterministic).

Sau cùng, tôi sẽ in ra so sánh metric đánh giá độ trễ thực thi latency/accuracy cho mọi người nhìn thấy trên tập 15 test questions để quyết định.

---

*File: reports/individual/2A202600285_QuachNgocQuang.md*

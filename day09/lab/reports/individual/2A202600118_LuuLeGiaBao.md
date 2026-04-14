# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Lưu Lê Gia Bảo
**Vai trò trong nhóm:** Supervisor Owner (Routing)  
**Ngày nộp:** 14-04-2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi chịu trách nhiệm triển khai "bộ não" điều hướng của hệ thống. Công việc của tôi là đảm bảo Supervisor có khả năng định tuyến các truy vấn của người dùng đến đúng worker chuyên biệt một cách hiệu quả và an toàn nhất.

**Module/file tôi chịu trách nhiệm:**

- File chính: `day09/lab/graph.py`
- Functions tôi implement: `supervisor_node`, `route_decision`, `human_review_node`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi nhận task từ cấu trúc `AgentState` mà A thiết kế, sau đó phân tích và ra quyết định định tuyến. Kết quả định tuyến của tôi sẽ quyết định xem C hay D sẽ là người thực thi tiếp theo. Ngoài ra, nếu tôi phát hiện rủi ro cao, tôi sẽ chuyển hướng qua node "Human Review" trước khi cho phép C tiếp tục tổng hợp dữ liệu.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
Tôi đã thiết lập logic keyword classification trong hàm `supervisor_node` với các tập hợp `policy_keywords` và `risk_keywords`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Triển khai cơ chế phân loại theo tầng (Tiered Classification) thay vì chỉ so khớp từ khóa đơn thuần.

**Lý do:**
Ban đầu, tôi định chỉ dùng một danh sách keyword chung. Tuy nhiên, qua thử nghiệm, tôi nhận thấy có những câu hỏi "giao thoa" (ví dụ: "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp"). Trong trường hợp này, nếu chỉ so khớp word-by-word, system có thể bị nhầm lẫn. Tôi đã chia logic thành các mức ưu tiên: ưu tiên Policy Auditor trước cho các yêu cầu cấp quyền, sau đó mới đến Retrieval cho các thông tin chung, và cuối cùng là ghi đè (override) bởi Human Review nếu có rủi ro cao.

**Trade-off đã chấp nhận:**
Việc này làm logic trong `supervisor_node` dài hơn và cần bảo trì danh sách từ khóa một cách cẩn thận. Tuy nhiên, nó giúp giảm thiểu việc định tuyến sai vào `retrieval_worker` khi task thực sự cần một công cụ chuyên biệt của `policy_tool_worker`.

**Bằng chứng từ trace/code:**

```python
# logic tiered trong supervisor_node
if any(kw in task for kw in policy_keywords):
    route = "policy_tool_worker"
    # ...
if risk_high and ("err-" in task or "không rõ" in task):
    route = "human_review"
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Supervisor không nhận diện được các từ khóa tiếng Việt có dấu.

**Symptom (pipeline làm gì sai?):**
Khi người dùng hỏi "khẩn cấp" hoặc "hoàn tiền", supervisor luôn chọn route mặc định là `retrieval_worker` thay vì `policy_tool_worker` hay `human_review`.

**Root cause:**
Query đầu vào chưa được xử lý đồng nhất về encoding và case-sensitivity, khiến việc so khớp `kw in task` bị thất bại do sự khác biệt giữa "Khẩn cấp" và "khẩn cấp".

**Cách sửa:**
Tôi đã thêm bước chuẩn hóa task bằng `.lower()` và đảm bảo bộ keyword được định nghĩa bằng lowercase. Đồng thời, tôi bổ sung thêm các biến thể từ khóa tiếng Việt phổ biến vào bộ `policy_keywords`.

**Bằng chứng trước/sau:**

- Trước: Query "HOÀN TIỀN" -> `route=retrieval_worker (default)`
- Sau: Query "HOÀN TIỀN" -> `route=policy_tool_worker`

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã xây dựng được một hệ thống routing minh bạch. Thông qua `route_reason`, người dùng có thể hiểu tại sao supervisor lại đưa ra quyết định đó, điều này cực kỳ hữu ích cho việc giải trình logic của AI.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Hệ thống của tôi vẫn phụ thuộc vào từ khóa cứng. Nếu người dùng dùng thuật ngữ quá xa lạ, hệ thống sẽ rơi vào route mặc định.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nếu supervisor không hoạt động, các worker chuyên biệt như `policy_tool_worker` của D sẽ không bao giờ được gọi, làm lãng phí toàn bộ nỗ lực xây dựng công cụ của nhóm.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc vào A để đảm bảo graph flow có thể quay lại worker sau khi HITL kết thúc.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thử kết hợp thêm một bộ phân loại xác suất nhỏ (như Naive Bayes) bên cạnh bộ từ khóa để tăng khả năng nhận diện ý định cho các câu hỏi mang tính diễn đạt tự nhiên hơn, thay vì chỉ dựa vào sự xuất hiện của từ khóa đơn lẻ.

---

_Lưu file này với tên: `reports/individual/B.md`_

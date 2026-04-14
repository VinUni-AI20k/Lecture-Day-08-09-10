# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Tiến Dũng
**Vai trò trong nhóm:** Worker Owner (policy_tool + synthesis)
**Ngày nộp:** 14/04/2026  
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

> Trong nhóm của tôi, tôi được phân công việc hoàn thiện policy_tool và synthesis.
> Ở Sprint 2, tôi làm hàm analyze_policy của policy_tool để làm thêm phần LLM để xử lý những policy và phân tích với role là 1 policy analyzer, nếu không có LLM thì sẽ fallback bằng phân tích theo hướng rule-based. Tôi còn làm thêm phần call_llm và estimate_confidence của file synthesis, ở hàm call_llm, tôi chỉ cần đặt trường hợp nên gọi llm nào và gọi llm đó theo cách gọi API riêng của từng LLM nhưng temperature được giảm để câu trả lời bám sát với thực tế hơn. Ở estimate_confidence, tôi cũng đặt 2 trường hợp: dùng llm với vai trò là 1 người đánh giá đáng tin cậy của response trên thang điểm 0-1 hay fallback sang cách tính đơn giản qua if-else
> Ở sprint 3 (Optional), tôi làm call_mcp_tool để gọi mcp_server có sẵn hoặc một real mcp tool khác. Nếu dùng mcp thật, tôi làm theo phương pháp nói chung là gửi response lên mcp và chờ nhận phản hồi, còn mcp_server thì đã có thể nhận nhanh hơn
**Module/file tôi chịu trách nhiệm:**
- File chính: `policy_tool.py và synthesis.py`
- Functions tôi implement: `_call_mcp_tool, analyze_policy, _call_llm, _estimate_confidence`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Ở Sprint 3, policy_tool phụ thuộc vào hàm dispatch_tool của file mcp_server.py nên nếu không dùng llm sẽ dựa vào hàm dispatch_tool để chờ đáp án. Và các file của tôi khi chạy Agent thì chúng đều phụ thuộc vào file retrieval.py để nhận text dù hoạt động độc lập với nhau

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
<img width="1708" height="848" alt="image" src="https://github.com/user-attachments/assets/b1894bb4-dc4a-4677-aad2-d824ecb40f09" />
<img width="1548" height="822" alt="image" src="https://github.com/user-attachments/assets/419b7ccb-0086-4eaf-b600-a4a61c0a9738" />
commit 7255c423929a1dae85c83e19f6ed7df6a0c6a219 (HEAD -> main)
Author: Nguyen Tien Dung <####@gmail.com>
Date:   Tue Apr 14 15:34:12 2026 +0700


_________________

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?
>Tôi và cả nhóm lựa chọn dùng LLM để chạy chương trình.
> Chúng tôi chọn LLm vì các lý do dưới đây
1. Vì cả nhóm đã có OpenAI API nên không dùng thì không tận dụng được các hàm dùng LLM
2. Khi truy xuất dữ liệu và chọn dữ liệu, LLM là một công cụ đóng vai trò phân tích và xử lý các tác vụ phức tạp hơn.
3. Để làm quen với mô hình A2A, MCP

**Quyết định:** Dùng LLM, còn những hàm có rule-based để phân tích thì làm cho phần Fallback

**Ví dụ:**
> "Tôi chọn dùng LLM thay vì tính heuristic.
> Kết quả: LLM có phần giải thích dựa trên dữ liệu xuất ra kết quả phân tích của nó, còn tính heuristic chỉ đo dựa trên độ dài văn bản và có thông tin hay không rồi xuất ra confidence 
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: 
- LLM:
Answer:
SLA cho ticket P1 là: 
- Phản hồi ban đầu trong 15 phút kể từ khi ticket được tạo.
- Xử lý và khắc phục trong 4 giờ.
- Tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút. [sla_p1_2026.txt]
Sources: ['sla_p1_2026.txt']
Confidence: 0.92
- heuristic: 
Answer:
[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env.

Sources: ['sla_p1_2026.txt']
Confidence: 0.92"

**Lý do:**
Để làm tăng tính xác thực cho điểm số confidence, tôi muốn chương trình giải thích từ dữ liệu như policy để người dùng hiểu rõ hơn.
_________________

**Trade-off đã chấp nhận:**
Để phân tích tốt hơn, LLM cần gọi API nên sẽ cần có thời gian chờ so với tính toán heuristic
_________________

**Bằng chứng từ trace/code:**
--- Test 2: Exception case ---
Heuristic confidence estimation took 1.00 seconds

Answer:
[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env.
Confidence: 0.83

LLM synthesis time: 10.73 seconds

Answer:
Khách hàng yêu cầu hoàn tiền cho đơn hàng Flash Sale do lỗi nhà sản xuất, nhưng theo chính sách, đơn hàng Flash Sale không được hoàn tiền. Điều này được quy định rõ trong tài liệu: "Đơn hàng Flash Sale không được hoàn tiền theo Điều 3 chính sách v4" [1].
Confidence: 0.83

```
[PASTE ĐOẠN CODE HOẶC TRACE RELEVANT VÀO ĐÂY]
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** Có 1 bug ở file khác chỉ rằng lỗi ở file policy_tool nhưng lỗi thực sự là ở file retrieval

**Symptom (pipeline làm gì sai?):**

File retrieval chưa làm xong nên có lỗi.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Chỉ thiếu File retrieval

**Cách sửa:**

Hoàn thành File retrieval

**Bằng chứng trước/sau:**

> Từ File Retrieval chưa hoàn chỉnh -> Hoàn chỉnh -> Xem file Retrieval

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

> Hoàn thành các công việc cần giao và tìm ra conflict giữa các công việc của nhóm.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

> Chưa kiểm tra xem agent đã chạy được, thụ động chờ hoàn thành project mới kiểm tra được

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

> Phần Policy_tool có hàm analyze_policy đã có cách xử lý sẵn nhưng sẽ không thể áp dụng LLM được   > nếu không thêm vào, và phần synthesis cũng tương tự

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

> Tôi chu yếu phụ thuộc file retrieval.py để kiểm tra xem file hoạt động tốt không.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)


> Tôi sẽ thử nghiệm chỉnh sửa role thêm khi dùng LLM như "1 analyzer" hay "1 data engineer" để kiểm > tra phản hồi nào tốt hơn 

_________________

---


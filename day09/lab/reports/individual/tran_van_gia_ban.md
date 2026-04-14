# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Văn Gia Bân  
**Vai trò trong nhóm:** Supervisor Owner
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

Trong Lab Day 09, tôi đảm nhận vai trò Supervisor Owner, chịu trách nhiệm thiết kế và triển khai kiến trúc luồng (Orchestration Layer) cho toàn bộ hệ thống đa tác tử.

**Module/file tôi chịu trách nhiệm:**
- File chính: `graph.py`
- Functions tôi implement: `make_initial_state (định nghĩa cấu trúc dữ liệu dùng chung), supervisor_node (xây dựng bộ định tuyến AI), route_decision (điều hướng edge), và build_graph (lắp ráp workflow vòng lặp đồ thị).`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

File graph.py của tôi là "trái tim" của hệ thống. Các worker (retrieval.py, policy_tool.py) do các thành viên khác viết sẽ chỉ là những đoạn script rời rạc nếu không có hệ thống đồ thị của tôi quản lý AgentState và phân phát task. Tôi định nghĩa cấu trúc I/O contract, nhận task từ user, và quyết định khi nào thì gọi worker của ai.
_________________

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

File: graph.py được tôi commit.
_________________

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** 

Nâng cấp cơ chế định tuyến từ Rule-based (If/Else Keyword Matching) sang LLM-based Semantic Routing với Structured Output (JSON) trong hàm supervisor_node.

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**

Ban đầu, tôi định dùng mảng từ khóa policy_keywords = ["hoàn tiền", "flash sale"]. Tuy nhiên, cách này cực kỳ thiếu linh hoạt. Nếu user dùng từ lóng hoặc mô tả vòng vèo (VD: "trả lại hàng đợt chớp nhoáng"), logic cứng sẽ thất bại. Tôi quyết định dùng gpt-4o-mini đóng vai trò là một Classifier, ép trả về định dạng JSON để hệ thống tự suy luận ngữ nghĩa của câu hỏi và quyết định route đi đâu.
_________________

**Trade-off đã chấp nhận:**

Đánh đổi tốc độ và chi phí lấy độ chính xác. Keyword routing chỉ mất ~0ms, trong khi gọi LLM mất ~1000ms đến 2000ms. Tuy nhiên, latency này hoàn toàn xứng đáng để hệ thống xử lý được các câu hỏi Multi-hop phức tạp.
_________________

**Bằng chứng từ trace/code:**

```
response = client.chat.completions.create(
            model="gpt-4o-mini", # Dùng model mini cho rẻ và nhanh, rất phù hợp làm Router
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task}
            ],
            response_format={"type": "json_object"}, # Ép trả về JSON
            temperature=0.1 # Để nhiệt độ thấp cho quyết định ổn định, logic
        )
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** Supervisor mất khả năng định tuyến thông minh do lỗi xác thực OpenAI API (AuthenticationError - 401).

**Symptom (pipeline làm gì sai?):**

Khi chạy graph.py với các câu hỏi về chính sách hay sự cố khẩn cấp, hệ thống không báo lỗi văng chương trình (crash) nhưng lại luôn luôn điều hướng mọi thứ vào retrieval_worker. Ở màn hình console, tôi thấy in ra dòng chữ cảnh báo màu vàng do khối try...except bắt được.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Lỗi nằm ở khâu cấu hình môi trường cho LLM Router. Giá trị OPENAI_API_KEY trong file .env bị thiếu hoặc sai ký tự. Khi khởi tạo client = OpenAI(), request gửi lên OpenAI bị từ chối với mã lỗi 401 (Invalid API Key). Nhờ cơ chế Fallback tôi đã viết trong hàm supervisor_node, thay vì làm sập toàn bộ Graph, nó tự động gán route = "retrieval_worker" để chương trình tiếp tục chạy.

**Cách sửa:**

Kiểm tra lại chuỗi API Key thật từ OpenAI platform và cập nhật chính xác vào file .env (không có dấu ngoặc kép thừa).

Đảm bảo đã import và gọi hàm load_dotenv() ngay ở đầu file graph.py để Python nạp đúng biến môi trường trước khi khởi tạo OpenAI Client.

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.

**Trước khi sửa:**  

python graph.py     
============================================================
Day 09 Lab — Supervisor-Worker Graph
============================================================

▶ Query: SLA xử lý ticket P1 là bao lâu?
⚠️ LLM Routing Error: Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-proj-**********************************************************************************************************************************************************gAaa. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}
  Route   : retrieval_worker
  Reason  : Fallback route due to LLM error
  Workers : ['retrieval_worker', 'retrieval_worker', 'synthesis_worker', 'synthesis_worker']
  Answer  : SYNTHESIS_ERROR: object of type 'NoneType' has no len()...
  Confidence: 0.0
  Latency : 1686ms
  Trace saved → ./artifacts/traces/run_20260414_211752.json

▶ Query: Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?
⚠️ LLM Routing Error: Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-proj-**********************************************************************************************************************************************************gAaa. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}
  Route   : retrieval_worker
  Reason  : Fallback route due to LLM error
  Workers : ['retrieval_worker', 'retrieval_worker', 'synthesis_worker', 'synthesis_worker']
  Answer  : SYNTHESIS_ERROR: object of type 'NoneType' has no len()...
  Confidence: 0.0
  Latency : 910ms
  Trace saved → ./artifacts/traces/run_20260414_211754.json

▶ Query: Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?
⚠️ LLM Routing Error: Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-proj-**********************************************************************************************************************************************************gAaa. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}
  Route   : retrieval_worker
  Reason  : Fallback route due to LLM error
  Workers : ['retrieval_worker', 'retrieval_worker', 'synthesis_worker', 'synthesis_worker']
  Answer  : SYNTHESIS_ERROR: object of type 'NoneType' has no len()...
  Confidence: 0.0
  Latency : 966ms
  Trace saved → ./artifacts/traces/run_20260414_211755.json

✅ graph.py test complete. Implement TODO sections in Sprint 1 & 2. 

**Sau khi sửa:**

python graph.py
============================================================
Day 09 Lab — Supervisor-Worker Graph
============================================================

▶ Query: SLA xử lý ticket P1 là bao lâu?
  Route   : retrieval_worker
  Reason  : Yêu cầu tra cứu thông tin về SLA xử lý ticket P1, không có rủi ro cao.
  Workers : ['retrieval_worker', 'retrieval_worker', 'synthesis_worker', 'synthesis_worker']
  Answer  : SLA xử lý ticket P1 là như sau:
- Phản hồi ban đầu: 15 phút kể từ khi ticket được tạo.
- Xử lý và kh...
  Confidence: 0.23
  Latency : 7071ms
  Trace saved → ./artifacts/traces/run_20260414_211933.json

▶ Query: Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?
  Route   : policy_tool_worker
  Reason  : Yêu cầu liên quan đến chính sách hoàn tiền cho sản phẩm lỗi.
  Workers : ['policy_tool_worker', 'policy_tool_worker', 'synthesis_worker', 'synthesis_worker']
  Answer  : Khách hàng yêu cầu hoàn tiền cho sản phẩm lỗi trong chương trình Flash Sale sẽ không được chấp nhận....
  Confidence: 0.14
  Latency : 4673ms
  Trace saved → ./artifacts/traces/run_20260414_211940.json

▶ Query: Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?
  Route   : policy_tool_worker
  Reason  : Yêu cầu liên quan đến quy trình cấp quyền, mặc dù có yếu tố khẩn cấp nhưng chủ yếu là về thủ tục.
  Workers : ['policy_tool_worker', 'policy_tool_worker', 'synthesis_worker', 'synthesis_worker']
  Answer  : Để cấp quyền Level 3 khắc phục sự cố P1 khẩn cấp, bạn cần thực hiện theo quy trình sau:

1. **Xác đị...
  Confidence: 0.15
  Latency : 6461ms
  Trace saved → ./artifacts/traces/run_20260414_211945.json

✅ graph.py test complete. Implement TODO sections in Sprint 1 & 2.

_________________

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

Tôi thiết kế được System Prompt rất chặt chẽ cho LLM Router, phân tách rõ ràng ranh giới giữa 3 node (Retrieval, Policy, Human Review). Nhờ đó, Routing Accuracy của nhóm đạt tỷ lệ rất cao (14/15 câu).

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Cơ chế Error Handling (Xử lý lỗi) cho LLM vẫn còn đơn giản. Hiện tại nếu gọi LLM Router bị timeout, tôi chỉ đang dùng try...except để gán cứng fallback về retrieval_worker. Ở môi trường production, cần có cơ chế Exponential Backoff (thử lại).

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Nếu file graph.py của tôi bị lỗi cú pháp hoặc định nghĩa sai key trong AgentState, code của tất cả các thành viên khác sẽ crash khi tích hợp (Integration) vì không có luồng dữ liệu hợp lệ.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Tôi phụ thuộc hoàn toàn vào tiến độ của các Worker Owners (người phụ trách retrieval.py, policy_tool.py, synthesis.py). Phần hệ thống Graph của tôi chỉ đóng vai trò là bộ khung điều phối luồng đi. Nếu họ không hoàn thành việc gọi AI và VectorDB thực tế ở bên trong các file đó, thì toàn bộ dữ liệu chạy qua hệ thống của tôi sẽ mãi chỉ là data giả lập (mock data) với các giá trị hard-code như confidence = 0.75 hay text [PLACEHOLDER]. Tôi cần họ hoàn thiện Worker để Graph có thể thực sự hoạt động với dữ liệu thật.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Tôi sẽ triển khai cơ chế Self-Correction (Tự sửa sai dạng vòng lặp đồ thị).

Lý do: Từ trace của câu gq10 (khách hỏi về Flash Sale), tôi thấy synthesis_worker trả về "confidence": 0.3 nhưng Graph vẫn đi thẳng đến kết thúc (END) và xuất câu trả lời thiếu chắc chắn.

Nếu có thêm 2 giờ, tôi sẽ thêm một conditional_edge sau node Synthesis trong graph.py: Nếu confidence < 0.5, hệ thống sẽ không dừng lại mà tự động quay ngược về retrieval_worker kèm theo yêu cầu: "Bằng chứng chưa đủ, hãy tìm thêm tài liệu mở rộng", tạo thành một ReAct Agent thực thụ.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*

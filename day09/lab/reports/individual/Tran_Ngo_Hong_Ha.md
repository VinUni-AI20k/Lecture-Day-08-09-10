# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:**  Trần Ngô Hồng Hà
**Vai trò trong nhóm:** Worker Owner
**Ngày nộp:** ___________  
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
- File chính: `retrieval.py`, `policy_tool.py`, `synthesis.py`
- Functions tôi implement: `retrieve_dense`, `_llm_judge_confidence`, `get_collection`, `_get_embedding_fn`
**Cách công việc của tôi kết nối với phần của thành viên khác:**

 - Hàm retrieve_dense là tool quan trọng để retrieve về các chunks có độ tương đồng ý nghĩa với querry của user, qua đó sử dụng làm context cho việc gen câu trả lời cho RAG Agent
 - Các hàm get_collection và _get_embedding_fn được tinh chỉnh lại để phù hợp với môi trường làm việc của tôi
 - _llm_judge_confidence là hàm sẽ gọi LLM thêm một lần nữa để đánh giá câu trả lời sát thế nào đối với context đã cung cấp. 

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
commit: 2a50c9b398f12814816392b45f4e5166a18da004, d6303eabf7d8530d297dfc374db828ea13d4e771
_________________

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Tôi chọn dùng rule-based check cho việc phân tích policy thay vì sử dụng LLM call trong policy_tool.py

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**

Với các policy trong bộ data này, các từ khóa gần như đã bao quát đầy đủ các trường hợp và khá rõ ràng, rule-based sẽ tối ưu chi phí và latency hơn so với LLM call

**Trade-off đã chấp nhận:**

Mặc dù hạn chế rõ ràng của rule-based sẽ là không phân tích và kiểm tra được các trường hợp câu hỏi mơ hồ, tuy nhiên các trường hợp đó rất ít trong giới hạn câu hỏi về policy, và sự đánh đổi về latency và chi phí token là không đáng

**Bằng chứng từ trace/code:**

```
# --- Rule-based exception detection ---
    exceptions_found = []

    # Exception 1: Flash Sale
    if "flash sale" in task_lower or "flash sale" in context_text:
        exceptions_found.append({
            "type": "flash_sale_exception",
            "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
            "source": "policy_refund_v4.txt",
        })

    # Exception 2: Digital product
    if any(kw in task_lower for kw in ["license key", "license", "subscription", "kỹ thuật số"]):
        exceptions_found.append({
            "type": "digital_product_exception",
            "rule": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt",
        })

    # Exception 3: Activated product
    if any(kw in task_lower for kw in ["đã kích hoạt", "đã đăng ký", "đã sử dụng"]):
        exceptions_found.append({
            "type": "activated_exception",
            "rule": "Sản phẩm đã kích hoạt hoặc đăng ký tài khoản không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt",
        })

    # Determine policy_applies
    policy_applies = len(exceptions_found) == 0
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** khi retrieve thì trả về zero chunks

**Symptom (pipeline làm gì sai?):**

Kết quả trả về khi chạy retrieval.py, index chạy và đọc collection vẫn ổn, chỉ có lúc trả về kết quả thì không retrieve được chunk nào

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Có vấn đề có thể được chỉ ra: 
- DIR_PATH: cách gán địa chỉ folder chứa dữ liệu bị sai quy cách nên không tìm được đến đúng thư mục
- hàm _get_embedding_fn: mặc dù khi cấu hình embed bằng OpenAI đúng model, nhưng vẫn có khả năng bị conflict model khi index và khi embed query


**Cách sửa:**

- Sửa cách gán biến địa chỉ thành hằng CHROMA_DB_DIR: str(Path(__file__).parent.parent / "chroma_db")
- Sửa lại hàm _get_embedding_fn bằng cách import trực tiếp hàm get_embedding từ file index

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.

_________________

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

tôi đã làm tốt trong việc implement các workers cho hệ thống Multi agent, đồng thời hỗ trợ mọi người trong quá trình kiểm thử và đánh giá kết quả

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Kỹ năng làm việc trên github của tôi còn chưa tốt, ngoài ra quá trình implement còn chậm do chưa biết cách tìm đúng vấn đề

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Nếu phần của tôi chưa xong, phần đánh giá kiểm thử sẽ bị chậm lại, tốn thêm thời gian cho việc đánh giá và quay lại nâng cấp hệ thống

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Phần việc của tôi không phụ thuộc nào thành viên khác, do các index tôi cũng đã tự triển khai dựa trên index của day08. Tuy nhiên, trong quá trình debug tôi vẫn cần có sự hỗ trợ từ Lead team

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> Tôi sẽ thử thêm phương pháp retrieval Hybrid, do kết quả của day08 cũng đã cho thấy với bộ dữ liệu đang có, Hybrid vượt trội hơn trong việc retrieve các chunks liên quan tới querry. Dense hiện tại đang thể hiện đủ tốt, tuy nhiên các trường hợp mà Sparse vượt trội hơn là không hiếm với bài toán này. Do đó, triển khai được Hybrid sẽ cải thiện kết quả một cách đáng kể.

_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*

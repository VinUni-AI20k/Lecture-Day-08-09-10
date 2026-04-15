# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Lâm Hoàng Hải
**Vai trò trong nhóm:** Worker Owner
**Ngày nộp:** 14/4/2026
**Độ dài yêu cầu:** 500–800 từ

---

> **Lưu ý quan trọng:**
>
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

- File chính: workers/policy_tool.py
- Functions tôi implement: `analyze_policy()` (Logic kiểm tra luật Hybrid) và `_call_mcp_tool()`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**

File worker của tôi hoạt động như một node kiểm duyệt nghiệp vụ trong graph. Nó nhận `retrieved_chunks` từ Retrieval Worker, sau đó đối chiếu với câu hỏi của khách hàng (`task`) để ra quyết định. Nếu thiếu thông tin (ví dụ cần tra cứu policy mới hoặc check ticket ID), worker của tôi sẽ gọi trực tiếp các tool từ `mcp_server.py` của MCP Owner (`search_kb`, `get_ticket_info`) trước khi tổng hợp kết quả output (`policy_applies`) trả về cho AgentState của Supervisor.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

0a6d694602e9d2318a023eafd99a258b980a6e1c

bacb65ac985976b99b137ea49fd201c2ba414ccf

---

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
>
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Tôi quyết định áp dụng kiến trúc **Hybrid Ensemble** kết hợp chạy song song Rule-based và LLM trong hàm `analyze_policy()` thay vì chỉ dùng 100% LLM.

---

**Lý do:** Khách hàng có thể vi phạm nhiều lỗi cùng lúc (Ví dụ: Vừa là hàng Flash Sale, vừa quá hạn 7 ngày). Nếu chỉ dùng LLM, việc prompt để bắt model liệt kê toàn bộ các lỗi thường tốn thời gian (latency cao) và có lúc bị sót.
Thay vào đó, tôi thiết kế hệ thống chạy qua 3 Phase:

- Phase 1: Dùng Rule-engine quét text (0ms) để nhặt ngay các lỗi hiển nhiên ("Flash sale", "đã kích hoạt").
- Phase 2: Dùng LLM quét sâu để đọc hiểu các lỗi ngữ nghĩa.
- Phase 3: Gộp kết quả của cả 2 Phase lại để đưa ra tập hợp lý do từ chối đầy đủ nhất.

---

**Trade-off đã chấp nhận:** Logic code phức tạp hơn nhiều so với việc gọi 1 API duy nhất. Tôi phải tốn thêm công viết thuật toán Deduplication (xóa trùng lặp) ở Phase 3 vì cả Rule và LLM có thể cùng văng ra một mã lỗi giống nhau cho cùng một vi phạm.

---

**Bằng chứng từ trace/code:**

```
Task: Tôi mua phần mềm diệt virus bản tải về, chưa nhập mã code, muốn trả lại.
  policy_applies: False
  top_rule: sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền
  top_source: llm_engine
  explanation: Hybrid Analysis. Rule-engine flags: 0. LLM Reasoning: Phần mềm diệt virus là sản phẩm kỹ thuật số...
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi: Trùng lặp dữ liệu ngoại lệ (Duplicated Exceptions) do xung đột giữa hai Engine.**

**Symptom (pipeline làm gì sai?):**

Khi khách hàng đưa ra một yêu cầu vi phạm luật rất rõ ràng (ví dụ: "hoàn tiền khóa học đã kích hoạt"), đầu ra của worker trả về 2 lỗi giống hệt nhau về bản chất. Điều này khiến AgentState bị phình to dữ liệu rác, làm nhiễu prompt của Synthesis Worker ở bước sau (Synthesis Worker xin lỗi khách hàng 2 lần vì cùng một lý do).

---

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Lỗi nằm ở logic ghép nối kiến trúc Hybrid. Phase 1 (Rule Engine) dò text thấy chữ "đã kích hoạt" nên ném ra một exception. Phase 2 (LLM Engine) đọc ngữ nghĩa cũng thấy vi phạm nên ném ra exception thứ hai. Cả 2 được nhồi chung vào một list mà không có màng lọc.

---

**Cách sửa:**

Tôi đã implement thêm **Phase 3 (Synthesis & Deduplication)**. Tôi gộp cả 2 mảng lỗi lại (`all_exceptions`), sau đó dùng cấu trúc dữ liệu `Set()` để lưu vết `seen_types`. Vòng lặp sẽ tự động loại bỏ các object lỗi bị trùng mã `type`, đảm bảo dữ liệu trả về cho Supervisor luôn sạch sẽ (Clean Data).

---

**Bằng chứng trước/sau:**

> Dán trace/log/output trước khi sửa và sau khi sửa.
> python
    # Phase 3: Synthesis & Deduplication
    all_exceptions = exceptions_found + llm_exceptions
    merged_exceptions = []
    seen_types = set()
    
    for ex in all_exceptions:
        if ex["type"] not in seen_types:
            merged_exceptions.append(ex)
            seen_types.add(ex["type"])

---

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

Thiết kế Schema Output chuẩn xác. Tôi đã map chính xác output của Worker với requirements trong `AgentState`. Đồng thời, tôi cũng thiết kế kiến trúc Hybrid có thể bắt được những từ đồng nghĩa trong exception.

---

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Thuật toán gộp lỗi (Deduplication) ở Phase 3 hiện tại chỉ lọc trùng lặp dựa trên exact match của field `type`. Nếu Rule và LLM sinh ra 2 loại type khác tên nhưng cùng bản chất ý nghĩa, mảng exception vẫn bị lặp data.

---

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Toàn bộ logic nghiệp vụ (quyết định cho hoàn tiền hay không) nằm ở file của tôi. Nếu tôi code sai rule, Synthesis Worker phía sau sẽ xin lỗi hoặc đồng ý sai với khách hàng, gây ảnh hưởng trực tiếp đến kết quả của chatbot.

---

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Tôi phụ thuộc vào RAG chunk từ Retrieval Worker phải cung cấp đủ và đúng ngữ cảnh chính sách. Đồng thời hàm `dispatch_tool` từ MCP Owner phải duy trì đúng cấu trúc Schema Interface đã thống nhất để gọi tool thành công.

---

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Tôi sẽ cải tiến thuật toán Deduplication (hợp nhất lỗi) ở Phase 3. Hiện tại trace cho thấy ở Test case "Khách hàng muốn hoàn tiền license key đã kích hoạt", Rule-engine trả về "digital_product_exception", nhưng LLM lại trả về "semantic_digital_exception" (bị lặp 2 lỗi cùng ý nghĩa). Tôi sẽ thử áp dụng Fuzzy Matching hoặc nhúng Semantic Similarity để gộp 2 lỗi này thành 1 trước khi đẩy kết quả ra AgentState, giúp dữ liệu log sạch và ngắn gọn hơn.

---

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*

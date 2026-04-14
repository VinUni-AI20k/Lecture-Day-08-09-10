# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Minh Quân - 2A202600181
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

> Trong dự án Lab Day 09, tôi chịu trách nhiệm thiết kế và triển khai "bộ não" điều phối của toàn bộ hệ thống tại file graph.py. Tôi trực tiếp định nghĩa AgentState (Shared State) — một hợp đồng dữ liệu dưới dạng TypedDict để đảm bảo tính nhất quán khi thông tin luân chuyển qua các worker.

**Module/file tôi chịu trách nhiệm:**
- File chính: `graph.py`
- Functions tôi implement: 
+ `supervisor_node`: Phân tích Task của người dùng thông qua kỹ thuật chuẩn hóa chuỗi và khớp từ khóa để quyết định lộ trình.

+ `route_decision`: Logic kiểm soát các cạnh điều kiện (Conditional Edges) để chuyển đổi giữa các trạng thái LangGraph.

+ `build_graph`: Xây dựng kiến trúc đồ thị, kết nối các Node (Retrieval, Policy, Human Review, Synthesis) thành một luồng thực thi hoàn chỉnh, bao gồm cả cơ chế Fallback khi môi trường thiếu thư viện LangGraph.

**Cách công việc của tôi kết nối với phần của thành viên khác:**

> Công việc của tôi đóng vai trò là "nhà ga trung tâm": Tiếp nhận đầu vào, phân phối việc cho Retrieval Worker hoặc Policy Worker, và đảm bảo Synthesis Worker nhận đủ log thực thi để phản hồi.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

> File graph.py với cấu trúc StateGraph(AgentState) và logic điều hướng keyword-based do tôi commit vào branch chính (Commit hash: 8f2a2f9 lúc 3:22 pm 14/04/2026)

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Tôi quyết định sử dụng Heuristic-based Routing (Chuẩn hóa NFKD + Keyword) thay vì gọi LLM Classifier để ra quyết định điều hướng tại supervisor_node.

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**

1. Hiệu suất (Latency): Việc gọi một LLM (như GPT-4o-mini hay Gemini Flash) chỉ để phân loại intent mất trung bình từ 600ms đến 1.2s. Trong khi đó, bộ lọc từ khóa được chuẩn hóa Unicode của tôi chỉ mất dưới 2ms.
2. Tính ổn định (Reliability): Với các nghiệp vụ cụ thể của Lab (SLA, Refund, Access Control), các từ khóa thường mang tính định danh rất cao. Tôi đã triển khai hàm _normalize sử dụng unicodedata để loại bỏ dấu tiếng Việt, giúp hệ thống nhận diện chính xác kể cả khi người dùng gõ không dấu (ví dụ: "hoan tien" vẫn nhận diện được "hoàn tiền").
3. Phân tầng ưu tiên: Tôi thiết lập logic ưu tiên Risk > Policy > Retrieval. Nếu phát hiện từ khóa rủi ro (P0, CISO, khẩn cấp), hệ thống sẽ ép buộc đi qua Human Review hoặc Retrieval thay vì các luồng tự động khác.

**Trade-off đã chấp nhận:**

> Chấp nhận rủi ro với các câu hỏi mang tính ẩn dụ hoặc không chứa từ khóa mục tiêu. Để khắc phục, tôi đã đặt retrieval_worker làm Default Route để đảm bảo luôn có bằng chứng tài liệu thay vì trả về lỗi rỗng.

**Bằng chứng từ trace/code:**

```
def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()

# Logic phân tầng rủi ro
if has_unknown_error_signal:
    route = "human_review" if risk_high else "retrieval_worker"
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:**:`UnicodeDecodeError` khi vận hành pipeline trên môi trường Windows và lỗi "State Inconsistency" giữa các Worker.

**Symptom (pipeline làm gì sai?):**

> Ban đầu, khi đọc các file policy hoặc lưu trace JSON, hệ thống thường xuyên bị crash với lỗi charmap codec can't decode. Ngoài ra, thông tin từ policy_result đôi khi không xuất hiện trong bước synthesis.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

1. Hệ điều hành Windows sử dụng CP1252 làm default encoding, trong khi dữ liệu Lab là UTF-8.
2. Trong hàm build_graph, các cạnh (edges) chưa được nối đúng dẫn đến việc một số node bị "cô lập", dữ liệu trả về từ worker không được merge vào state chung của LangGraph.

**Cách sửa:**

1. Tôi đã đồng bộ hóa toàn bộ các hàm open() và json.dump() với tham số encoding="utf-8".
2. Tôi cấu trúc lại AgentState với total=False và sử dụng state.setdefault trong từng node để đảm bảo các list như history hay worker_io_logs luôn tồn tại và được cộng dồn (append) thay vì ghi đè.

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.
''JSON''
"history": [
    "[supervisor] route=policy_tool_worker needs_tool=True ...",
    "[policy_tool_worker] Analysis complete ...",
    "[synthesis_worker] final answer generated"
],
"latency_ms": 25

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

> Tôi đã xây dựng được một hệ thống có tính Observability (khả năng quan sát) cao. Việc thiết kế worker_io_logs và hàm save_trace giúp nhóm có thể xem lại chính xác từng mili-giây và từng bước logic của Agent, rất hữu ích cho việc debug RAG.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

> Phần human_review_node của tôi hiện tại vẫn chỉ là một placeholder đơn giản. Tôi chưa triển khai được cơ chế interrupt_before thực thụ của LangGraph để dừng pipeline chờ tín hiệu từ API bên ngoài.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

> Tôi nắm giữ cấu trúc State. Nếu tôi thay đổi tên biến (ví dụ từ retrieved_chunks thành docs), toàn bộ worker của các thành viên khác sẽ bị lỗi KeyError.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

> Tôi phụ thuộc hoàn toàn vào output của Retrieval Worker. Nếu kết quả vector search trả về không đúng format list, hàm Synthesis do tôi điều phối sẽ không thể tạo ra câu trả lời cuối cùng.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:

> Tôi sẽ cải tiến supervisor_node bằng cách thêm một lớp LLM Semantic Router dự phòng. Dựa trên trace của query "Can cap quyen Level 3...", tôi nhận thấy nếu người dùng dùng từ lóng, keyword matching có thể bị sót. Tôi muốn dùng một model nhỏ (như Llama 3-8B) để verify lại quyết định routing khi confidence của keyword matching thấp dưới một ngưỡng nhất định.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*

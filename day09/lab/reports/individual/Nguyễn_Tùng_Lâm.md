# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Tùng Lâm   
**Vai trò trong nhóm:** Trace & Docs Owner  
**Ngày nộp:** 14/4/2026  
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
- File chính: `system_architecture.md, single_vs_multi_comparison.md `
- Functions tôi implement: `N/A — vai trò Docs Owner: viết và duy trì tài liệu kiến trúc, bảng so sánh metrics, shared state schema, và debug trace analysis`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Theo dõi tiến độ quá trình làm việc và tổng kết các kết quả đi theo flow làm việc đúng như nhóm đã đề ra ban đầu

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

system_architecture.md, single_vs_multi_comparison.md 

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Ghi nhận và phân tích lựa chọn **LLM Routing (Option B)** thay vì Keyword Matching (Option A) trong `system_architecture.md` — lựa chọn này tôi đề xuất ghi lại dưới dạng bảng so sánh có bằng chứng từ trace thay vì chỉ mô tả chung chung.

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**

LLM Routing linh hoạt hơn keyword matching vì supervisor dùng `gpt-4o-mini` hiểu ngữ nghĩa câu hỏi — khi user dùng từ đồng nghĩa hoặc câu hỏi mơ hồ, LLM vẫn route đúng thay vì miss keyword. Tôi ghi lại quyết định này trong `system_architecture.md` mục 5 với bảng so sánh 6 tiêu chí và quan sát thực tế từ trace.

**Trade-off đã chấp nhận:**

Latency tăng thêm ~1 LLM call mỗi request (supervisor call). Đo được trong `single_vs_multi_comparison.md`: Day 08 avg 2203ms → Day 09 avg 4378ms (+2175ms). Với câu đơn giản thì overhead không đáng — tôi đã ghi nhận giới hạn này trong mục 6 `system_architecture.md` và đề xuất hybrid routing (keyword match trước, LLM fallback khi không match rõ).

**Bằng chứng từ trace/code:**

```
# system_architecture.md — mục 5, quan sát thực tế:
- "LLM Routing (Option B) linh hoạt hơn keyword matching: Supervisor dùng gpt-4o-mini
   hiểu ngữ nghĩa câu hỏi, không bị sai khi user dùng từ đồng nghĩa."
- "Fallback an toàn: Nếu LLM Supervisor lỗi (timeout, hết quota),
   hệ thống tự động về retrieval_worker thay vì crash."

# single_vs_multi_comparison.md — Metrics:
| Avg latency (ms) | 2203 | 4378 | +2175ms | Day 09 thêm LLM supervisor + MCP calls |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A |
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** `get_ticket_info` và `create_ticket` không có trong `TOOL_REGISTRY` — tài liệu ban đầu ghi không chính xác rằng MCP server có 3 tools hoạt động đầy đủ.

**Symptom (pipeline làm gì sai?):**

Khi tôi viết `system_architecture.md` mục MCP Server, tôi list `get_ticket_info` như một tool hoạt động. Nhưng khi nhóm chạy pipeline với câu hỏi liên quan ticket P1, answer thiếu thông tin emergency bypass — không thấy `get_ticket_info` trong `mcp_tools_used` của trace.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Lỗi ở MCP layer: `get_ticket_info` và `create_ticket` đã implement trong `mcp_server.py:162–276` nhưng bị comment out khỏi `TOOL_REGISTRY`. Policy worker có code gọi `get_ticket_info` (dòng 201) nhưng nhận về error dict thay vì data thực. Tôi phát hiện khi đọc code để điền bảng MCP tools trong tài liệu.

**Cách sửa:**

Cập nhật tài liệu `system_architecture.md` để phản ánh đúng thực tế: chỉ 2 tools hoạt động (`search_kb`, `check_access_permission`). Đồng thời ghi nhận giới hạn này vào mục 6 và thông báo nhóm để fix bằng cách gọi `check_access_permission` trực tiếp thay vì `get_ticket_info`.

**Bằng chứng trước/sau:**

```
# TRƯỚC — system_architecture.md mục MCP Server (sai):
| get_ticket_info | ticket_id | ticket details, priority, status |   ← ghi là hoạt động

# SAU — sau khi sửa (đúng):
| get_ticket_info | N/A | Đã implement (mcp_server.py:162) nhưng không có trong
                          TOOL_REGISTRY — chưa hoạt động  |

# Bằng chứng từ group debug trace (single_vs_multi_comparison.md dòng 111-112):
"Xem mcp_tools_used → phát hiện get_ticket_info trả về error dict
 vì tool không có trong TOOL_REGISTRY (bị comment out)"
```

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

Tổng hợp và cấu trúc thông tin từ nhiều nguồn (code, trace, team discussion) thành tài liệu rõ ràng. Cụ thể: bảng Shared State Schema trong `system_architecture.md` (15 fields với mô tả ai đọc/ghi) và bảng metrics trong `single_vs_multi_comparison.md` có số liệu thực tế (confidence, latency, abstain rate) thay vì ước đoán — nhóm dùng trực tiếp để nộp báo cáo.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

`routing_decisions.md` còn bỏ trống — tôi chưa kịp điền 3 routing decisions từ trace thực tế vì phụ thuộc vào kết quả từ thành viên chạy pipeline. Ngoài ra, không nắm sâu phần code implementation nên một số chi tiết kỹ thuật phải hỏi lại thành viên khác mới ghi được chính xác.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

`docs/system_architecture.md` là tài liệu tham chiếu chính để nhóm đồng bộ contract giữa các workers — nếu tôi ghi sai Shared State Schema hoặc vai trò từng component, các thành viên implement worker có thể dùng sai field name. Group report cũng phụ thuộc vào `single_vs_multi_comparison.md` để điền metrics section.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Cần kết quả chạy pipeline thực tế (trace output, latency measurements, routing distribution) từ thành viên Supervisor Owner và Worker Owner để điền đầy đủ `routing_decisions.md` và mục grading questions trong group report. Nếu không có trace, tôi chỉ có thể ghi cấu trúc tài liệu mà không có số liệu xác thực.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Cải tiến thêm và có lẽ thử thêm các phương pháp khác

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*

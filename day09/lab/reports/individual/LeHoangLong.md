# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Lê Hoàng Long  
**Vai trò trong nhóm:** Supervisor Owner / Worker Owner / MCP Owner / Trace & Docs Owner  
**Ngày nộp:** 14-4-2026  
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
- File chính: `mcp-server.py`
- Functions tôi implement: `get_ticket_info`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Tìm hiểu các đoạn mã do các thành viên viết bằng tay cũng như dùng AI để viết 

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

def get_ticket_info(ticket_id: str):
    """MCP Tool: Get ticket information from mock DB."""
    ticket = TICKET_DB.get(ticket_id)
    if ticket:
        return {"ticket": ticket, "status": "success"}
    else:
        # Fallback to the first P1 if not found for demo
        if "P1" in ticket_id:
            return {"ticket": TICKET_DB["P1-LATEST"], "status": "found_fallback"}
        return {"error": "Ticket not found", "status": "failed"}


---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Tôi không có nhiều quyết định, chủ yếu quyết định đều do AI đề xuất, tôi kỳ vọng rằng đợt nghỉ lễ 30-4 và 1-5 sẽ cho tôi khoảng thời gian để làm lại toàn bộ các bài lab, do lượng kiến thức đổ vào lớn và nhanh nên cần thời gian đẻ thực sự hiểu chúng và hiểu những đoạn mã do AI sinh ra. 

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**

_________________

**Trade-off đã chấp nhận:**

_________________

**Bằng chứng từ trace/code:**

```
[PASTE ĐOẠN CODE HOẶC TRACE RELEVANT VÀO ĐÂY]
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** ___________________

**Symptom (pipeline làm gì sai?):**

_________________

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

_________________

**Cách sửa:**

_________________

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.

_________________

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**
Tôi sử dụng vibe coding để hoàn thành công việc

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Tôi chưa thể ghi  chú được tất cả các luồng xử lý được sinh ra bởi AI

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

_________________

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

sprint 1 và sprint 2

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*

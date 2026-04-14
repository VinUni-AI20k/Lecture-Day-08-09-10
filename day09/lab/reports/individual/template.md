# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** ___________  
**Vai trò trong nhóm:** Supervisor Owner / Worker Owner / MCP Owner / Trace & Docs Owner  
**Ngày nộp:** ___________  
**Độ dài yêu cầu:** 500–800 từ

---

<<<<<<< HEAD
> **Lưu ý quan trọng:**
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm
> - Deadline: Được commit **sau 18:00** (xem SCORING.md)
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`)
=======
> **Lưu ý quan trọng (để tránh mất điểm cá nhân):**
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm.
> - Mỗi phần phải có **bằng chứng cụ thể**: file, function, trace id hoặc commit.
> - Nội dung phân tích phải khác hoàn toàn với thành viên khác.
> - Deadline: được commit sau 18:00 (xem `SCORING.md`).
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`).

## Checklist bắt buộc trước khi nộp

- [ ] Có nêu rõ file/function tôi trực tiếp làm.
- [ ] Có ít nhất 1 quyết định kỹ thuật + trade-off.
- [ ] Có ít nhất 1 bug fix thực tế + before/after evidence.
- [ ] Có đề cập mối liên hệ phần tôi làm với output nhóm.
- [ ] Không có claim nào trái với code/trace hiện có.
>>>>>>> NhatVi

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

> Mô tả cụ thể module, worker, contract, hoặc phần trace bạn trực tiếp làm.
> Không chỉ nói "tôi làm Sprint X" — nói rõ file nào, function nào, quyết định nào.

**Module/file tôi chịu trách nhiệm:**
- File chính: `___________________`
- Functions tôi implement: `___________________`
<<<<<<< HEAD
=======
- Contract/trace fields tôi đụng tới: `___________________`
>>>>>>> NhatVi

**Cách công việc của tôi kết nối với phần của thành viên khác:**

_________________

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

<<<<<<< HEAD
_________________
=======
- Commit: `___________________`
- File liên quan: `___________________`
- Trace id/run id liên quan: `___________________`
>>>>>>> NhatVi

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** ___________________

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

<<<<<<< HEAD
=======
**Liên kết sang file/trace thật (bắt buộc điền):**
- File code: `___________________`
- Trace file/id: `___________________`

>>>>>>> NhatVi
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

<<<<<<< HEAD
_________________
=======
- Trước khi sửa: `___________________`
- Sau khi sửa: `___________________`
- File đã sửa: `___________________`
>>>>>>> NhatVi

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

_________________

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

_________________

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

_________________

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

_________________

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

_________________

---

<<<<<<< HEAD
=======
## Self-check chống 0/40

- [ ] Tôi giải thích được rõ phần mình khai báo khi bị hỏi trực tiếp.
- [ ] Claim trong báo cáo khớp `workers_called`, `route_reason`, `mcp_tools_used` (nếu có).
- [ ] Không copy câu chữ/ý chính từ báo cáo cá nhân thành viên khác.

>>>>>>> NhatVi
*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*

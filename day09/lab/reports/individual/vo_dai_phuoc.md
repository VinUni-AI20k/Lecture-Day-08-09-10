# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Võ Đại Phước 
**Vai trò trong nhóm:** MCP Owner  
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
- file chính: mcp_server.py
- Tập trung vào function `tool_search_kb`, `tool_check_access_permission`, các tool ko làm thì comment, chỉnh lại `TOOL_SCHEMAS`
- chỉnh lại `ACCESS_RULES` để match với [file](day09/lab/data/docs/access_control_sop.txt)

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Sau khi dev xong thì làm việc với sprint-2 owner (dev về worker) để check worker sẽ gọi tool

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
[commit hash](3a9299fd9e11d894b2eff0e60489c790af07ba23), [PR](https://github.com/BanBannBannn/Lab8-C401-Y3/pull/13)

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?


**Quyết định:** thêm điều kiện kiểm tra `requester_role` trong khi implement `tool_check_access_permission`

**Lý do:**
Cần kiểm trả role của người request phải đạt yêu cầu khi Access level, nếu không tương ứng với level thì can_grant = False

**Trade-off đã chấp nhận:**
Không có

**Bằng chứng từ trace/code:**

```
if requester_role not in rule['required_approvers']:
    can_grant = False
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** Trong implementation của tool, hàm trả về data type không đúng key với `TOOL_SCHEMAS`

**Symptom (pipeline làm gì sai?):**
Không thiếu triệu chứng, check code thì thấy sai

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**
Do viết code giữa hàm function và define `TOOL_SCHEMAS` không đồng nhất với nhau

**Cách sửa:**

dùng @tool decorator của langchain để hỗ  trợ tạo tool schema tốt hơn, đỡ phải double check

**Bằng chứng trước/sau:**

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**
Kiểm trả kỹ yêu cầu trước khi làm, double check với tài liệu, không làm qua loa

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Chưa implement để có thể trở thành MCP thật sự (gọi request đến MCP server)

**Nhóm phụ thuộc vào tôi ở đâu?**
Tool chưa xong thì người làm worker ở sprint 2 có thể không chạy được code

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

không có
---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tham gia vào việc đánh giá granding đầu ra, vì trace tương đối nhiều, cần phải kiểm tra manual để có thể check
performance của retrieval worker

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*

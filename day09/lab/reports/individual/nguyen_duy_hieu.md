# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** member_1  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 2026-04-14

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong buổi lab này, tôi phụ trách toàn bộ lớp retrieval ở `workers/retrieval.py`. Phần tôi làm không chỉ là “lấy top_k chunks” mà là giữ cho evidence đi ra từ worker này đủ sạch để các worker phía sau không bị nhiễu. Tôi tập trung vào các hàm `_tokenize()`, `_lexical_score()`, `_line_score()`, `_best_line_for_doc()`, `_pick_hint_doc()` và `retrieve_dense()`. Ngoài ra, tôi chỉnh thêm local fallback để ưu tiên tài liệu đúng intent: refund, SLA/P1, access control, HR và helpdesk. Công việc của tôi kết nối trực tiếp với `workers/synthesis.py` vì nếu retrieval trả nhầm chunk yếu hoặc sai nguồn thì confidence và citation của toàn pipeline sẽ tụt ngay. Nói ngắn gọn: tôi chịu trách nhiệm cho “đầu vào bằng chứng” của cả hệ.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** tôi dùng chiến lược hybrid giữa lexical scoring và dense retrieval, đồng thời thêm intent-based doc hints cho local fallback.

Tôi cân nhắc hai phương án: (1) chỉ dùng dense retrieval từ ChromaDB, hoặc (2) kết hợp dense + lexical + hint theo tài liệu. Tôi chọn phương án (2) vì Day09 có nhiều câu tiếng Việt pha keyword tiếng Anh, ví dụ “license key”, “P1”, “refund”, “access”. Dense retrieval thuần thường tốt về ngữ nghĩa, nhưng trong một số câu ngắn và có con số, nó dễ kéo nhầm chunk broad. Lexical score giúp tăng độ chính xác cho keyword hiển thị trực tiếp trong câu hỏi, còn doc hints giúp local fallback không bị “mù đường” khi ChromaDB yếu hoặc thiếu. Trade-off là ranking có thể hơi thiên về tài liệu có từ khóa rõ, nhưng đổi lại hệ trả lời ổn định hơn trên tập test thật. Trace cuối sprint cho thấy các query như `q01`, `q02`, `q06`, `q08` đều lấy đúng tài liệu gốc nhờ cách này.

**Bằng chứng từ code:**

```python
blended_score = 0.7 * dense_similarity + 0.3 * lexical_score
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** các câu hỏi numeric hoặc incident dễ nhận về chunk broad, ví dụ heading của tài liệu hoặc đoạn mô tả quá chung, làm câu trả lời không có số liệu đúng.

**Symptom (pipeline làm gì sai?):** khi hỏi kiểu “bao lâu”, “mấy ngày”, “sau bao nhiêu phút”, retrieval thường trả về chunk có từ khóa trùng nhưng không chứa con số quan trọng. Kết quả là synthesis vẫn trả lời được nhưng confidence thấp hoặc trích nhầm thông tin.

**Root cause:** local fallback lúc đầu ưu tiên overlap từ khóa quá đơn giản, chưa phân biệt câu hỏi số với câu hỏi định tính. Ngoài ra, các heading lớn như “=== Phần 3: Quy trình xử lý sự cố P1 ===” thường lọt vào top vì có keyword mạnh nhưng không đủ factual.

**Cách sửa:** tôi bổ sung `_is_numeric_query()` và `_contains_number()` để tăng điểm cho line có số khi câu hỏi cần số, đồng thời giảm điểm cho heading broad. Tôi cũng giữ chặt top line theo tài liệu thay vì để nhiều chunk yếu chen vào.

**Bằng chứng trước/sau:** các query numeric như `q01`, `q02`, `q06` và `q11` sau đó trả về line có số cụ thể như “1 ngày làm việc”, “10 phút”, “mỗi 30 phút”.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

Điểm mạnh nhất của tôi là giữ cho retrieval ổn định trên cả tài liệu dài lẫn câu hỏi ngắn có nhiều tín hiệu. Tôi không chỉ sửa code cho chạy, mà cố gắng làm cho evidence thật sự đáng tin để worker sau không phải đoán. Điểm tôi chưa làm thật hoàn hảo là numeric fidelity vẫn chưa phải mức tuyệt đối; một số câu rất phức tạp vẫn cần thêm heuristic hoặc answer-level judge. Nhóm phụ thuộc vào tôi ở chỗ nếu retrieval trả sai nguồn, synthesis và policy đều dễ đi lệch theo. Ngược lại, tôi phụ thuộc vào member_2 và member_3 để policy/ confidence xử lý tốt phần còn lại sau khi evidence đã được kéo đúng.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thêm một tầng chunking theo câu thay vì chỉ đọc line thô từ file, rồi viết test riêng cho numeric questions. Lý do là trace hiện tại cho thấy numeric queries vẫn là điểm yếu lớn nhất trong phần grounding. Nếu có thêm 2 giờ, tôi cũng muốn tăng số test case có “mấy bước / bao lâu / bao nhiêu ngày” để đo xem retrieval mới có cải thiện thật hay chỉ tốt trên vài câu mẫu.

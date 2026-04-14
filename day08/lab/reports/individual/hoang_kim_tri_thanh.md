# Báo Cáo Cá Nhân — Hoàng Kim Trí Thành

**Họ và tên:** Hoàng Kim Trí Thành  
**MSSV:** 2A202600372  
**Vai trò trong nhóm:** Nhóm trưởng — điều phối, review code, tích hợp branch, tối ưu pipeline  
**Ngày nộp:** 13/04/2026

## 1. Tôi đã làm gì trong lab này?

Trong lab Day 08, tôi đảm nhận vai trò nhóm trưởng, phụ trách điều phối toàn bộ tiến trình phát triển và trực tiếp tham gia vào phần tối ưu pipeline. Cụ thể, công việc của tôi chia thành ba mảng chính:

Thứ nhất là **thiết lập hạ tầng ban đầu**: dựng FastAPI server (`api_server.py`) làm cầu nối giữa frontend và backend, cấu hình CORS, biến môi trường `.env`, và đảm bảo ChromaDB index chạy ổn định với 29 chunk từ 5 tài liệu nguồn.

Thứ hai là **review và merge branch** của các thành viên. Tổng cộng có 6 lần merge chính vào `main`: 3 đợt từ Tú Anh (abstain logic, citation grounding, adversarial test), 1 đợt từ Gia Dược (retrieval flow), 1 đợt từ Quốc Dũng (eval/scorecard), và 1 đợt từ Thành Nam (docs). Mỗi lần merge tôi đều đọc diff, kiểm tra xung đột logic, và chạy thử pipeline trước khi nhập.

Thứ ba là **tối ưu pipeline cuối cùng**: sau khi nhận được bộ `grading_questions.json`, tôi chạy benchmark hệ thống để đo baseline (69/98 điểm), phân tích failure mode từng câu, rồi lần lượt điều chỉnh `top_k_select` (3→8), `WEAK_CONTEXT_SCORE_THRESHOLD` (0.15→0.05), và viết lại prompt từ v1 (6 rules) sang v2 (9 rules). Kết quả cuối đạt 83/98 điểm, tương đương 25.4/30.

## 2. Điều tôi hiểu rõ hơn sau lab này

Lab này giúp tôi hiểu rằng chất lượng câu trả lời của RAG phụ thuộc rất lớn vào **retrieval depth** — tức là pipeline đưa bao nhiêu chunk vào context cho LLM. Trước lab, tôi nghĩ chọn top-3 chunk tốt nhất là đủ, vì ít context = ít noise. Nhưng thực tế cho thấy với 29 chunk từ 5 tài liệu, nhiều câu hỏi cần thông tin từ 2–3 section khác nhau trong cùng một document (ví dụ: gq05 cần cả scope ở Section 1 lẫn điều kiện Level 4 ở Section 2). Top-3 không đủ bao phủ.

Tôi cũng hiểu sâu hơn về **false abstain**: ngưỡng `WEAK_CONTEXT_SCORE_THRESHOLD` ban đầu (0.15) nghe có vẻ hợp lý nhưng lại chặn nhầm chunk hợp lệ có cosine score khoảng 0.12. Việc hạ threshold phải đi kèm với prompt rule đủ mạnh ở lớp L3 để LLM tự biết khi nào context thực sự không đủ.

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Điều ngạc nhiên nhất là hybrid retrieval (dense + BM25) lại **thua** dense trên bộ test của nhóm. Khi đọc lý thuyết, tôi kỳ vọng hybrid sẽ tốt hơn vì kết hợp cả ngữ nghĩa lẫn keyword matching. Nhưng thực tế, RRF score sau khi merge ranking của dense và BM25 có scale rất thấp (~0.016), gây ra hai vấn đề: (1) chunk BM25 ít liên quan về ngữ nghĩa lọt vào pool và làm loãng context, (2) score thấp trigger false abstain nếu giữ nguyên threshold 0.15. Tôi phải sửa code để threshold chỉ áp dụng cho dense mode.

Khó khăn lớn nhất là **tối ưu citation behavior của LLM**. Dù prompt v2 yêu cầu "cite đúng snippet cho từng fact", LLM vẫn có xu hướng gom hết citation vào `[1]` — đặc biệt khi chunk [1] chứa gần đủ thông tin. Đây là giới hạn ở tầng model, không phải retrieval.

## 4. Phân tích câu gq05: Contractor cần Admin Access — điều kiện?

**Câu hỏi:** *Một contractor bên ngoài cần quyền Admin Access Level 4 để thực hiện dự án. Quy trình yêu cầu cấp quyền gồm những bước gì và ai phê duyệt?*

Ở baseline (top_k_select=3, threshold=0.15), pipeline trả về "Không đủ dữ liệu trong tài liệu để trả lời" — tức abstain sai. Trace log cho thấy ChromaDB trả về chunk từ `access_control_sop.txt` nhưng cosine score chỉ ~0.12, thấp hơn threshold 0.15 → bị chặn ở lớp L2 (weak score guard). Ngoài ra, top-3 chunk chỉ chứa Section 2 về Level 4 detail mà thiếu Section 1 về scope ("áp dụng cho employee, contractor, third-party vendor").

**Root cause**: failure xảy ra ở tầng **retrieval** (thiếu depth) kết hợp **guard logic** (threshold quá cao).

**Fix áp dụng**:
1. Hạ `WEAK_CONTEXT_SCORE_THRESHOLD` từ 0.15 xuống 0.05 — chunk score 0.12 vượt ngưỡng.
2. Tăng `top_k_select` từ 3 lên 8 — LLM nhìn thấy cả Section 1 (scope: contractor) lẫn Section 2 (Level 4: IT Manager + CISO approve, 5 ngày review, security training).
3. Prompt v2 thêm rule "scope + applicability": nếu snippet khai báo scope, kết hợp scope với detail section thay vì abstain.

Sau fix, gq05 đạt **Full** (5/5/5/5). Đây là câu cải thiện nhiều nhất (+10 raw points) và là minh chứng rõ nhất cho việc tăng retrieval depth giải quyết multi-section coverage.

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Hai hướng cải tiến cụ thể dựa trên scorecard:

1. **Rerank với cross-encoder** cho top-8: thay vì chọn 8 chunk theo cosine score, dùng `ms-marco-MiniLM-L-6-v2` rerank để đẩy chunk hotline (gq06 — ext. 9999) lên top. Code rerank đã implement nhưng chưa bật do A/B ban đầu chưa có evidence đủ mạnh.

2. **Query decomposition** cho gq02 và gq06: tách câu hỏi multi-hop thành sub-queries (ví dụ: "VPN policy?" + "device limit?") rồi retrieve riêng, merge context. Cách này giúp mỗi sub-query có chunk pool chuyên biệt hơn, tránh tình trạng LLM gom citation sai.

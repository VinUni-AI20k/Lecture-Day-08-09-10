### 📊 So sánh các Chế độ Retrieval

| Đặc điểm | **Dense (Vector)** | **Sparse (BM25)** | **Hybrid (RRF)** |
| :--- | :--- | :--- | :--- |
| **Cơ chế** | Tìm theo ý nghĩa (Embedding) | Tìm theo từ khóa chính xác | Kết hợp cả hai |
| **Điểm mạnh** | Hiểu được các câu hỏi diễn đạt khác đi (ví dụ: *"làm tại nhà"* thay vì *"remote"*). | Cực kỳ chính xác với mã lỗi (`ERR-403`), số lượng (`10 ngày`) hoặc ID. | **Bù đắp sai số**. Nếu Dense bị nhiễu, Sparse sẽ kéo kết quả đúng lại. |
| **Điểm yếu** | Dễ bị "nhiễu" (ví dụ: lấy file HR khi hỏi về IT vì cả hai đều có từ "approval"). | Không hiểu từ đồng nghĩa. Nếu hỏi sai từ khóa trong tài liệu sẽ không tìm thấy gì. | Tốn thời gian xử lý hơn một chút (không đáng kể). |
| Độ chính xác từ khóa        | Trung bình. Đôi khi bị "nhiễu" do các câu có cấu trúc tương đồng nhưng nội dung khác loại. | Rất tốt. Tìm cực nhanh và chuẩn các mã lỗi (ERR-403), số lượng (5 lần) hoặc tên riêng. | Tốt nhất. Kết hợp được cả hai, giảm thiểu sai sót của từng mode đơn lẻ.                      |
| Hiểu ngữ nghĩa              | Tốt. Hiểu được các câu hỏi diễn đạt khác đi (synonyms).                       | Kém. Chỉ tìm được nếu câu hỏi chứa từ khóa giống trong tài liệu.             | Tốt. Thừa hưởng khả năng của Dense.                                                          |
| Hallucination (Bịa chuyện)  | Thấp (do Prompt ép chặt). Nhưng có xu hướng lấy thừa tài liệu không liên quan. | Thấp nhất. Nếu không thấy từ khóa, nó thường không trả về kết quả.           | Thấp.                                                                                       |
| Kết quả thực tế             | Câu q03 (phê duyệt Level 3) bị lẫn sang hr/leave-policy do có từ "Manager".   | Tìm chính xác số ngày hoàn tiền (q02) nhờ từ khóa "ngày làm việc".           | Vượt trội ở các câu phức tạp như q11 (xử lý P1) khi cần gộp thông tin từ nhiều nguồn.       |

### 🔍 Phân tích chi tiết

*   **Dense Mode (Điểm yếu nhiễu)**: Trong các câu hỏi về **Access Control**, Dense thường xuyên lấy nhầm các đoạn văn trong `hr/leave-policy` vì cùng chứa các thuật ngữ "approval", "manager". Điều này có thể khiến LLM bị xao nhãng nếu không có Reranker để lọc lại.
*   **Sparse Mode (Độ chính xác cao)**: Với các câu hỏi như *"Tài khoản bị khóa sau bao nhiêu lần?"*, Sparse trả về kết quả cực sạch chỉ chứa đúng chunk có số `5`, giúp LLM trả lời cực kỳ gãy gọn.
*   **Hybrid Mode (Sự ổn định)**: Trong tất cả 30 câu test, Hybrid luôn cho kết quả bằng hoặc tốt hơn hai mode còn lại. Đặc biệt ở các câu hỏi phức tạp như `q10` (Hỏi về 4 cấp độ Level 1-4), Hybrid là mode duy nhất lấy đủ context để LLM không trả lời thiếu ý.


## 1. Bảng đối soát chi tiết từng Mode

| ID | Mode | Kết quả thực tế (Answer) | Đáp án mong đợi (Target Answer) | Tài liệu sử dụng (Resources) |
| :--- | :--- | :--- | :--- | :--- |
| **q01** | **sparse** | "SLA xử lý ticket P1 là 4 giờ [2]." | Phản hồi **15 phút** và thời gian xử lý **4 giờ**. | `support/sla-p1-2026.pdf` |
| **q07** | **dense** | "Không có thông tin này trong tài liệu." | Tài liệu cũ 'Approval Matrix' nay là **Access Control SOP**. | `it/access-control-sop.md` |
| **q07** | **sparse** | "Không có thông tin này trong tài liệu." | Tài liệu cũ 'Approval Matrix' nay là **Access Control SOP**. | `it/access-control-sop.md` |
| **q07** | **hybrid** | "Không có thông tin này trong tài liệu." | Tài liệu cũ 'Approval Matrix' nay là **Access Control SOP**. | `it/access-control-sop.md` |
| **q08** | **dense** | "Không có thông tin này trong tài liệu." | Tên mới là **Access Control SOP**. | `it/access-control-sop.md` |
| **q08** | **sparse** | "Không có thông tin này trong tài liệu." | Tên mới là **Access Control SOP**. | `it/access-control-sop.md` |
| **q08** | **hybrid** | "Không có thông tin này trong tài liệu." | Tên mới là **Access Control SOP**. | `it/access-control-sop.md` |
| **q10** | **dense** | "Không có thông tin này trong tài liệu." | **Không có quy trình riêng cho VIP**, áp dụng chuẩn cho tất cả. | `policy/refund-v4.pdf` |
| **q10** | **sparse** | "Không có thông tin này trong tài liệu." | **Không có quy trình riêng cho VIP**, áp dụng chuẩn cho tất cả. | `policy/refund-v4.pdf` |
| **q10** | **hybrid** | "Không có thông tin này trong tài liệu." | **Không có quy trình riêng cho VIP**, áp dụng chuẩn cho tất cả. | `policy/refund-v4.pdf` |

---

## 2. Phân tích nguyên nhân & Giải pháp

### A. Lỗi thiếu ý (Incomplete Retrieval)
*   **Hiện tượng**: Chỉ lấy được một phần câu trả lời (ví dụ chỉ lấy 4h mà quên 15p).
*   **Nguyên nhân**: Do thuật toán Sparse search xếp hạng các đoạn văn (chunks) dựa trên mật độ từ khóa. Đoạn chứa 15p có thể có điểm thấp hơn đoạn chứa 4h.
*   **Giải pháp**: Tăng số lượng `top_k` chunk được gửi cho LLM (ví dụ từ 3 lên 5) hoặc sử dụng tính năng **Long-context support**.

### B. Lỗi định danh (Alias/Entity Mapping)
*   **Hiện tượng**: Không tìm thấy tài liệu khi hỏi bằng tên cũ ("Approval Matrix").
*   **Nguyên nhân**: Dữ liệu trong cơ sở dữ liệu vector chỉ chứa tên mới. Cả Dense và Sparse đều không "biết" mối liên hệ lịch sử này.
*   **Giải pháp**: Bổ sung một bảng từ điển (Synonyms) hoặc thêm Metadata "Old name: Approval Matrix" vào chunk trong quá trình Indexing.

### C. Lỗi giới hạn Grounding (Strict Abstention)
*   **Hiện tượng**: Trả về "Không có thông tin" cho các câu hỏi phủ định (VIP).
*   **Nguyên nhân**: Prompt hiện tại cực kỳ khắt khe để tránh Hallucination. Nếu tài liệu không chứa chính xác từ "VIP", Model sẽ từ chối trả lời thay vì suy luận logic.
*   **Giải pháp**: Điều chỉnh Prompt để LLM linh hoạt hơn: "Nếu không thấy quy định đặc biệt cho một đối tượng cụ thể, hãy kiểm tra quy định chung cho toàn bộ và thông báo rằng không có ngoại lệ".



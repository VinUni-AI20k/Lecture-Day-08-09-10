# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** C401 - B4  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Nguyễn Thị Thùy Trang | Tech Lead | nuyenthuytrang372004@gmail.com |
| Trần Việt Phương | Retrieval Owner | phuong251202@gmail.com |
| Lê Đức Anh | Retrieval Owner | ducanh198369@gmail.com |
| Phạm Hoàng Tiến Mạnh | Eval Owner |  |
| Nguyễn Ngọc Tân | Eval Owner |  |
| Nguyễn Hoàng Nghĩa | Eval Owner | nhnghia210@gmail.com |
| Trịnh Uyên Chi | Documentation Owner | trinhuyenchi2003@gmail.com |

**Ngày nộp:** 13/04/2026

**Repo:** https://github.com/phuongub/Lab08_B4_C401.git

**Độ dài khuyến nghị:** 600–900 từ

---

## 1. Pipeline nhóm đã xây dựng (150–200 từ)

**Chunking decision:**
> Nhóm quyết định chọn chunk_size=500 và overlap=50 kết hợp cắt đệ quy (Recursive). Kích thước 500 tokens là "điểm cân bằng" lý tưởng: đủ lớn để bao trọn một quy trình Helpdesk (tránh đứt gãy ngữ cảnh), đồng thời đủ nhỏ để không tạo ra nhiễu thông tin khi trả lời các câu hỏi FAQ ngắn. Mức overlap 50 tokens (~10%) hoạt động như "bản lề" kết nối, giúp bảo toàn các cấu trúc điều kiện logic thường thấy trong IT Helpdesk (VD: "Nếu ticket P1 không xử lý trong 2h...") trong trường hợp câu văn bị vắt ngang giữa hai chunk.

_________________

**Embedding model:** 
> Sử dụng text-embedding-3-preview. Mô hình này cân bằng cực tốt giữa chi phí và tốc độ, đồng thời có khả năng biểu diễn không gian vector ổn định cho dữ liệu tiếng Việt trộn lẫn nhiều mã lỗi/thuật ngữ tiếng Anh đặc thù của khối IT Helpdesk.

_________________

**Retrieval variant (Sprint 3):**
> Nhóm chọn bổ sung luồng Rerank (Cross-encoder). Lý do: Dense Search thường vấp phải lỗi "tương đồng giả" (nhầm lẫn giữa các chính sách có chung từ vựng). Chiến lược của nhóm là dùng Dense để kéo về Top 10 chunk thô (lấy rộng), sau đó dùng sức mạnh đối chiếu chéo (cross-attention) của Reranker để chấm điểm và lọc lại Top 3. Việc này giải quyết triệt để hiện tượng kéo sai ngữ cảnh, đảm bảo LLM sinh câu trả lời chuẩn xác.

_________________

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Nâng cấp chiến lược truy xuất từ Dense Search thuần túy lên luồng Pipeline hai bước: Lấy mẫu rộng bằng Dense Search + Lọc tinh bằng Cross-encoder Rerank.

**Bối cảnh vấn đề:** Đặc thù tài liệu IT Helpdesk chứa rất nhiều điều khoản có bộ từ vựng chồng lấp hoặc sử dụng các tên gọi cũ/alias (ví dụ: "Approval Matrix"). Ở phiên bản Baseline, Dense Search không đủ độ nhạy bén để phân biệt các chi tiết siêu nhỏ này. Hệ quả là vector của chunk đúng và chunk sai nằm rất sát nhau, khiến hệ thống liên tục kéo nhầm các chunk nhiễu (noise) lên Top đầu.

_________________

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Hybrid Retrieval (Dense + BM25) | Cải thiện khả năng bắt trúng các từ khóa chính xác (mã lỗi, mã ticket). Tốc độ xử lý nhanh (low latency). | Vẫn gặp khó khăn khi từ khóa xuất hiện ở nhiều nơi không liên quan. Không có khả năng "hiểu" sâu mối quan hệ giữa câu hỏi và từng chunk. |
| Dense + Rerank (Cross-encoder) | Độ chính xác (Precision) cao nhất. Có khả năng đối chiếu chéo (cross-attention) để phân biệt các chi tiết siêu nhỏ giữa các chunk tương đồng. | Tăng thời gian phản hồi (latency) do phải chạy thêm một mô hình chấm điểm sau khi retrieval. |

**Phương án đã chọn và lý do:**

Nhóm quyết định chọn Dense + Rerank (Cross-encoder).

Lý do chọn: Trong nghiệp vụ hỗ trợ kỹ thuật, tính chính xác tuyệt đối quan trọng hơn tốc độ phản hồi. Reranker hoạt động như một "chuyên gia" đọc lại toàn bộ Top 10 kết quả thô, phân tích sự tương quan tinh tế nhất giữa câu hỏi và bối cảnh để đẩy đúng chunk chứa câu trả lời lên vị trí ưu tiên. Với các câu hỏi chứa tên cũ (alias) như "Approval Matrix", Reranker đã chứng minh khả năng lọc bỏ hoàn toàn các chunk nhiễu mà ngay cả Hybrid Search cũng có thể bỏ sót.

**Bằng chứng từ scorecard/tuning-log:**

Kết quả thực nghiệm cho thấy điểm Faithfulness tăng từ 3.30 lên 5.00 (+1.70). Đặc biệt ở câu q07, dù Retrieval mang về nhiều thông tin gây nhiễu về quy trình truy cập, Reranker đã nhận diện chính xác đoạn chứa thông tin "alias" để phục vụ câu trả lời, thay vì bị đánh lạc hướng bởi các đoạn văn bản có mật độ từ khóa cao nhưng không liên quan.

---

## 3. Kết quả grading questions (100–150 từ)

**Ước tính điểm raw:** 98 / 98

**Câu tốt nhất:** ID: ___ — Lý do: ___________________

**Câu fail:** ID: gq05 — Root cause: gq05 fail không phải vì không retrieve được tài liệu, mà vì pipeline chưa đủ mạnh để suy luận và ghép evidence thành kết luận cuối cùng.

Cụ thể, câu hỏi này yêu cầu tổng hợp hai mảnh thông tin trong cùng một SOP: Section 1 nói contractor nằm trong phạm vi áp dụng, còn Section 2 mới nói Admin Access, approver, 5 ngày và training. Tức là answer đúng phải được “compose” từ nhiều chunk, không phải copy từ một câu explicit trong doc. Trong scorecard_variant.md, gq05 vẫn có Context Recall = 5 nhưng Faithfulness/Completeness thấp, điều đó cho thấy retrieval đã lấy đúng evidence, nhưng generation không dám kết luận.

**Câu gq07 (abstain):** Với gq07, pipeline xử lý đúng theo hướng abstain: tài liệu hiện có không chứa mức phạt, nên hệ thống không hallucinate mà trả về câu trả lời an toàn thay vì bịa thông tin.

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

> Dựa vào `docs/tuning-log.md`. Tóm tắt kết quả A/B thực tế của nhóm.

**Biến đã thay đổi (chỉ 1 biến):** Rerank

| Metric | Baseline | Variant | Delta |
|--------|---------|---------|-------|
| Faithfulness | 3.30/5 | 5.00/5 | 1.70 |
| Relevance | 3.22/5 | 4.90/5 | 1.68 |
| Context Recall | 3.90/5 | 5.00/5 | 1.10 |
| Completeness | 3.00/5 | 4.40/5 | 1.40 |

**Kết luận:**
> Variant vượt trội hoàn toàn và áp đảo Baseline trên tất cả các phương diện. 
* Điểm trung thực (Faithfulness) chạm mức tối đa tuyệt đối (5.00/5, tăng vọt 1.70 điểm). Điều này chứng tỏ AI không còn tự bịa thông tin mà đã bám sát 100% vào tài liệu Helpdesk.
* Khả năng gom ngữ cảnh (Context Recall) đạt điểm tuyệt đối 5.00. Luồng retrieval mới đã sửa được lỗi "kéo nhầm rác", mang về đầy đủ và chính xác các chunk tài liệu cần thiết.
* Độ liên quan (Relevance) tăng mạnh (+1.68) cho thấy câu trả lời của AI đánh trực diện vào câu hỏi của người dùng (hit the point), đồng thời độ chi tiết (Completeness) cũng được cải thiện đáng kể (+1.40).
_________________

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Trang | Tech Lead | 1+2 |
| Phương | Retrieval Owner | 1+3 |
| Đức Anh | Retrieval Owner | 1+3 |
| Mạnh | Eval Owner | 3+4 |
| Nghĩa | Eval Owner | 3+4 |
| Tân | Eval Owner | 3+4 |
| Chi | Documentation Owner | 4 |

**Điều nhóm làm tốt:**

Chiến lược phân mảnh (Chunking): Lựa chọn đúng phương pháp tách theo tiêu đề (Heading-based) kết hợp đệ quy, giúp bảo toàn trọn vẹn ngữ cảnh logic của các quy trình SLA vắt chéo nhiều đoạn văn.

**Điều nhóm làm chưa tốt:**

Nhóm đã quá chủ quan với sự ổn định của API bên thứ ba. Khi chạy chấm điểm hàng loạt, lỗi Rate Limit/Timeout liên tục làm sập hệ thống, nhưng do không có cơ chế lưu tạm (Checkpointing), nhóm phải mất hàng giờ đồng hồ chạy lại từ đầu.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> Tích hợp Checkpoint & Auto-Retry: Xây dựng cơ chế tự động thử lại và lưu kết quả tạm thời vào file local cho Evaluation Loop, chấm dứt hoàn toàn cảnh sập pipeline và mất trắng dữ liệu do lỗi API.

_________________

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*

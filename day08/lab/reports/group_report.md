# Group Report — Day 08 RAG Pipeline

## Tóm tắt
Nhóm đã xây dựng thành công pipeline RAG nội bộ dành cho khối CS + IT Helpdesk nhằm trả lời các câu hỏi về chính sách và quy trình kỹ thuật. Hệ thống trải qua 4 giai đoạn phát triển:
1. **Indexing:** Sử dụng ChromaDB làm vector store với mô hình embedding local `Alibaba-NLP/gte-multilingual-base`.
2. **Retrieval:** Triển khai Dense Retrieval cơ bản và nâng cấp bằng kỹ thuật Rerank.
3. **Generation:** Sử dụng LLM Groq (`llama-3.1-8b-instant`) làm mặc định để đảm bảo tốc độ phản hồi nhanh.
4. **Evaluation:** Thiết lập hệ thống LLM-as-Judge tự động chấm điểm dựa trên 4 metrics cốt lõi.

## Danh sách thành viên và Phân vai (Nhóm 5 người)
| Thành viên | Vai trò chính | Trách nhiệm chính |
| :--- | :--- | :--- |
| **Phạm Đan Kha** | Tech Lead | Tích hợp hệ thống, quản lý API Groq và xây dựng cơ chế Fallback xử lý lỗi. |
| **Trần Đặng Quang Huy** | Indexing Owner | Preprocess tài liệu, xây dựng chiến lược chunking và quản lý metadata trong ChromaDB. |
| **Vũ Đức Kiên** | Retrieval Owner | Implement `retrieve_dense`, chuẩn hóa dữ liệu đầu ra và thiết lập logic abstain chống bịa thông tin. |
| **Phan Anh Khôi** | Eval Owner | Xây dựng bộ chấm điểm LLM-as-Judge và trực tiếp triển khai mô hình Rerank cho Sprint 3. |
| **Nguyễn Duy Hiếu** | Documentation Owner | Phân tích Root Cause từ log đánh giá, hoàn thiện tài liệu kiến trúc và nhật ký tuning. |

## Kết quả chính
* **Sprint 1:** Hoàn thành tiền xử lý 5 tài liệu, chia nhỏ thành 30 chunks với kích thước 400 tokens và overlap 80 tokens, đảm bảo giữ đủ metadata `source`, `section`, và `effective_date`.
* **Sprint 2:** Xây dựng thành công Baseline RAG có khả năng trích dẫn nguồn `[1]` và từ chối trả lời (abstain) chính xác cho các câu hỏi ngoài phạm vi như mã lỗi `ERR-403-AUTH`.
* **Sprint 3:** Triển khai biến thể Rerank sử dụng Cross-encoder (`ms-marco-MiniLM-L-6-v2`) để tối ưu hóa việc chọn lọc Top-3 context.
* **Sprint 4:** Chạy scorecard tự động cho 10 câu hỏi test. Kết quả cho thấy biến thể Rerank vượt trội so với Baseline về độ đầy đủ thông tin.

## Quan sát từ evaluation
* **Sự cải thiện vượt trội:** Điểm **Completeness (Độ đầy đủ)** tăng mạnh từ **3.30 lên 4.40 (+1.10)** khi bật Rerank.
* **Khắc phục lỗi Retrieval:** Ở câu hỏi q02 về thời hạn hoàn tiền, Baseline bị lỗi (điểm 1/5) do bốc nhầm chunk quy trình; Rerank đã sửa thành công (điểm 5/5) bằng cách đẩy đúng chunk chứa thông tin "7 ngày" lên vị trí ưu tiên.
* **Tính an toàn cao:** Cả Baseline và Variant đều đạt điểm **Faithfulness (Độ trung thực) tuyệt đối** ở các câu hỏi bẫy, chứng minh prompt grounding hoạt động rất hiệu quả.
* **Đánh đổi Latency:** Việc sử dụng Rerank và LLM-as-Judge làm tăng độ trễ (latency) của hệ thống nhưng mang lại chất lượng câu trả lời ổn định và giàu chứng cứ hơn.

## Deliverables đã hoàn thành
* Mã nguồn: `index.py`, `rag_answer.py`, `eval.py`
* Dữ liệu & Log: `data/test_questions.json`, `logs/grading_run.json`
* Kết quả đánh giá: `results/scorecard_baseline.md`, `results/scorecard_variant.md`
* Tài liệu: `docs/architecture.md`, `docs/tuning-log.md`
* Báo cáo: `reports/group_report.md` và 5 file báo cáo cá nhân

## Kết luận
Pipeline RAG của nhóm đã vận hành ổn định và đáp ứng đầy đủ yêu cầu từ Sprint 1 đến Sprint 4. Thông qua thực nghiệm, nhóm xác định **Rerank** là biến thể mang lại giá trị lớn nhất trong việc nâng cao chất lượng câu trả lời cho các câu hỏi chính sách phức tạp. Hệ thống sẵn sàng cho việc triển khai Grading chính thức.

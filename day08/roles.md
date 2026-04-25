### 📊 PHÂN VAI CHI TIẾT (TEAM 7 NGƯỜI)

| Role | Thành viên | Nhiệm vụ cốt lõi | Deliverables chịu trách nhiệm |
|:---|:---|:---|:---|
| **Tech Lead** | **Dũng, Quang** | Code chính, ghép nối các module (Pair programming). Setup môi trường, fix bug pipeline. | `index.py`, `rag_answer.py`, `eval.py` |
| **Retrieval Owner** | **Tuấn, Hải** | Nghiên cứu file text để chia chunk, bóc tách metadata. Implement thuật toán Hybrid/Rerank. | Code logic Chunking & Tuning Variant |
| **Eval Owner** | **Huy, Long** | Đọc data tạo test case chặn đầu. Chạy file đánh giá, chấm điểm Baseline vs Variant. | `test_questions.json`, `scorecard_*.md` |
| **Doc Owner / Scrum Master**| **Thuận** | Ghi chép thiết kế, log tuning, viết file doc chuẩn chỉnh. Giục team viết báo cáo cá nhân. | `architecture.md`, `tuning-log.md` |

---

### 🏃‍♂️ KẾ HOẠCH TÁC CHIẾN QUA 4 SPRINTS

#### Sprint 1 (60') — Build Index
*Mục tiêu: Đưa được data vào DB có kèm metadata.*

*   **Dũng + Quang (Tech Lead):** Clone source, `pip install`, setup `.env`. Viết hàm `get_embedding()`, setup kết nối ChromaDB trong `index.py`.
*   **Tuấn + Hải (Retrieval):** Đọc lướt 5 file `data/docs/`. Quyết định chiến lược cắt chunk (theo ký tự, hay theo Regex/Heading?). Viết hàm bóc tách 3 metadata: `source`, `section`, `effective_date`. Đưa logic cho Tech Lead ghép vào code.
*   **Huy + Long (Eval):** Đọc file policies, soạn ngay 10 câu hỏi vào `test_questions.json` (phải có cả câu dễ và câu "bẫy" cần metadata như "Quy định năm 2026").
*   **Thuận (Doc):** Mở `architecture.md`, vẽ/viết mô tả cấu trúc hệ thống lúc đầu (Vector DB gì, Embeddings model gì).

#### Sprint 2 (60') — Baseline Retrieval + Answer
*Mục tiêu: Hỏi đáp được, có trích dẫn nguồn.*

*   **Dũng + Quang (Tech Lead):** Viết `retrieve_dense()` lấy data từ ChromaDB. Viết `call_llm()` truyền context vào prompt.
*   **Tuấn + Hải (Retrieval):** Hỗ trợ Tech Lead viết System Prompt sao cho LLM biết cách trích dẫn `[1]`, `[2]` và biết từ chối (abstain) nếu không có thông tin. Test thử bằng tay vài câu.
*   **Huy + Long (Eval):** Rà soát lại bộ câu hỏi. Chuẩn bị hàm/kịch bản để chạy tự động 10 câu hỏi này qua LLM.
*   **Thuận (Doc):** Cập nhật `architecture.md` phần Prompt Design và Baseline config.

#### Sprint 3 (60') — Tuning Tối Thiểu
*Mục tiêu: Nâng cấp chất lượng tìm kiếm.*

*   **Tuấn + Hải (Retrieval):** **(LEAD)** Quyết định chọn 1 Variant (Khuyên dùng: **Hybrid Search** vì IT Helpdesk có nhiều mã lỗi/từ khoá cứng, hoặc **Rerank**). Cùng Tech Lead code variant này vào `rag_answer.py`.
*   **Dũng + Quang (Tech Lead):** Cấu trúc lại code để dễ dàng switch qua lại giữa Baseline và Variant.
*   **Huy + Long (Eval):** **(LEAD)** Hoàn thiện `eval.py`. Chạy thử đánh giá trên Baseline trước để lấy mốc điểm (Scorecard).
*   **Thuận (Doc):** Mở file `tuning-log.md`. Phỏng vấn Tuấn + Hải: *"Tại sao lại chọn Variant này? Giả thuyết là gì?"* và ghi chú lại.

#### Sprint 4 (60') — Evaluation + Docs + Report
*Mục tiêu: Đóng gói, chạy A/B test và nộp bài.*

*   **Huy + Long (Eval):** Chạy lệnh `compare_ab()` giữa Baseline và Variant. Xuất file scorecard, phân tích xem Variant có thật sự tốt hơn không.
*   **Dũng + Quang (Tech Lead):** Gom code, clean code, xoá print rác. Test lại lệnh end-to-end: `python index.py && python rag_answer.py && python eval.py`.
*   **Thuận (Doc):** **(LEAD)** Lấy kết quả từ team Eval đập vào `tuning-log.md`. Hoàn thiện toàn bộ Document. Nhắc nhở 6 người kia tạo file trong `reports/individual/`.
*   **CẢ TEAM 7 NGƯỜI:** Dành 15 phút cuối cùng, ai tự viết file báo cáo cá nhân của người nấy (500-800 từ) lưu vào `reports/individual/[ten_cua_ban].md`.

---

### 💡 Lời khuyên để team chạy mượt:
1. **Chia sẻ màn hình:** Đừng mỗi người code một góc. Dũng và Quang nên share màn hình Discord/Meet hoặc dùng VSCode Live Share để Tuấn/Hải nhìn vào đọc logic chunking.
2. **Không block nhau:** Team Eval (Huy, Long) và Doc (Thuận) không cần đợi code xong mới làm. Hãy dùng dữ liệu giả (mock data) hoặc template để viết trước.
3. **Focus vào Definition of Done:** Tuân thủ đúng A/B Rule ở Sprint 3 - **CHỈ ĐỔI 1 BIẾN**. Đừng tham làm cả Rerank lẫn Hybrid cùng lúc sẽ không kịp giờ đánh giá.
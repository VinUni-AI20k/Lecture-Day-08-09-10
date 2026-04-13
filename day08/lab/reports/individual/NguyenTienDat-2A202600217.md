# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Tiến Đạt — 2A202600217
**Vai trò trong nhóm:** Retrieval Enhancement Owner (Sprint 2 & 3)
**Ngày nộp:** 2026-04-13
**Độ dài:** ~700 từ

---

## 1. Tôi đã làm gì trong lab này?

Tôi đảm nhận phần **cải tiến retrieval** trong Sprint 2 và Sprint 3, tập trung vào ba hướng
độc lập được đánh dấu trong `rag_answer.py`.

Trong **Sprint 2**, tôi thêm **Smart Abstain Detection**: trước khi gọi LLM, pipeline kiểm
tra `max(cosine_score)` của các candidates. Nếu điểm cao nhất dưới ngưỡng
`ABSTAIN_THRESHOLD = 0.20`, hệ thống trả về câu từ chối ngay mà không tốn thêm một API
call nào. Lý do chọn cách này thay vì chỉ dùng prompt-instruction: LLM đôi khi bỏ qua
"hãy nói không biết" và hallucinate — kiểm tra ở retrieval stage đảm bảo cắt hoàn toàn.

Trong **Sprint 3**, tôi implement hai kỹ thuật nâng cao:

- **HyDE (Hypothetical Document Embeddings)**: Thay vì embed câu hỏi gốc, tôi dùng LLM
  sinh một đoạn "câu trả lời giả định" (hypothetical answer) bằng ngôn ngữ tài liệu nội bộ,
  rồi embed đoạn đó để search. Phần này kết hợp với BM25 qua RRF (weight 0.65/0.35) thành
  `retrieve_hyde()`.

- **Multi-Query Fusion (RAG-Fusion)**: Dùng LLM sinh 2 cách diễn đạt khác của query gốc,
  retrieve với từng cách bằng hybrid, rồi fuse kết quả bằng RRF. Mục tiêu là tăng recall cho
  các paraphrase queries.

Ngoài ra tôi implement `rerank()` với CrossEncoder và `reorder_for_lost_in_middle()` — hai
hàm hỗ trợ bổ sung cho generation quality.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

**Khoảng cách giữa embedding của câu hỏi và embedding của câu trả lời là vấn đề có hệ thống.**

Trước lab, tôi mặc định rằng nếu LLM tốt và prompt đủ rõ thì RAG sẽ hoạt động. Sau khi debug
`retrieve_hyde()`, tôi hiểu vấn đề sâu hơn: vector embedding của câu hỏi *"Approval Matrix
là tài liệu nào?"* và embedding của chunk *"Access Control SOP — Quy trình cấp quyền hệ
thống"* nằm xa nhau trong không gian vector, dù về ngữ nghĩa chúng liên quan chặt chẽ. Đây
là mismatch cơ bản giữa query distribution và document distribution — dense retrieval không
bridge được gap này.

HyDE giải quyết bằng cách thêm bước trung gian: LLM đã biết rằng "Approval Matrix" thường
được tái đặt tên thành "Access Control SOP", nên hypothetical answer sẽ dùng đúng thuật ngữ
→ embedding gần chunk thật hơn nhiều. Đây là insight tôi sẽ nhớ lâu: **retrieval thất bại
im lặng nguy hiểm hơn LLM hallucination** vì không có error message, pipeline vẫn trả về
"câu trả lời" — chỉ là từ sai source.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

**Khó khăn chính: RRF score không thể dùng làm abstain threshold.**

Khi implement Smart Abstain cho `retrieve_dense()` với cosine score, logic `max_score < 0.20`
hoạt động tốt — cosine score mang ý nghĩa tuyệt đối. Nhưng khi áp cùng threshold cho HyDE và
Hybrid, tôi nhận ra RRF score luôn nhỏ xấp xỉ `~0.016` cho dù kết quả có liên quan hay
không (vì công thức `1 / (k + rank)` bị chia cho hằng số lớn). Pipeline abstain nhầm gần như
mọi hybrid query.

Giải pháp: phân tách logic — `should_abstain()` chỉ chạy với mode `dense` và `sparse` (có
score tuyệt đối); với `hybrid`/`hyde`/`multi_query`, để LLM tự abstain qua grounded prompt
(rule 2: "Nếu Context không có thông tin → từ chối"). Đây là trường hợp điển hình của
**abstraction leak**: tôi đã assume một interface chung cho các retrieval modes mà thực tế
semantics của `score` hoàn toàn khác nhau giữa dense và RRF.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi q07:** *"Approval Matrix để cấp quyền hệ thống là tài liệu nào?"*

Đây là câu hỏi **hard** vì dùng tên cũ ("Approval Matrix") trong khi tài liệu hiện tại có
tên "Access Control SOP". Không có chunk nào chứa chuỗi "Approval Matrix" trong corpus.

**Baseline (Dense):**
Context Recall ≈ 1/5. Dense embed câu hỏi trực tiếp → cosine similarity với chunk
`access_control_sop` thấp → không retrieve được đúng source. Câu trả lời: mơ hồ hoặc
abstain nhầm. Lỗi nằm ở **retrieval**, không phải indexing hay generation.

**Variant 1 (Hybrid):**
Context Recall tăng lên ≈ 2-3/5. BM25 match từ "cấp quyền" và "hệ thống" đủ để kéo
`access_control_sop` lên rank cao hơn. Cải thiện, nhưng alias vẫn chưa được resolve.

**Variant 2 (HyDE):**
Context Recall ≈ 5/5. LLM sinh hypothetical answer dùng đúng cụm "Access Control SOP" →
embedding khớp chunk thật → retrieve chính xác. Câu trả lời có citation `[1]` từ đúng tài
liệu. Đây là case study rõ ràng nhất cho thấy **query-document distribution mismatch** là
root cause, và HyDE là targeted fix cho vấn đề đó.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Tôi sẽ **benchmark Multi-Query Fusion trên q06 và q10** vì eval hiện tại chưa có số liệu
cụ thể. Kết quả tuning-log cho thấy HyDE giải quyết alias (q07) tốt, nhưng multi-hop queries
(q06: escalation cross-document) và edge cases (q10: VIP refund không có trong docs) vẫn chưa
có variant rõ ràng. Giả thuyết: Multi-Query với 3 variants sẽ tăng Recall cho q06 thêm
+1/5, trong khi q10 cần corpus addition chứ không phải retrieval fix.

---

*File: `reports/individual/nguyen_tien_dat.md`*
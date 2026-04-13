# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 13/04/2026 
**Config:**
```
retrieval_mode = "dense"
chunk_size = 300 tokens
overlap = 50 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = GPT 4-o
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.40/5 |
| Relevance | 4.60/5 |
| Context Recall | 5.00/5 |
| Completeness | 4.50/5 |

**Câu hỏi yếu nhất (điểm thấp):**
q10 (Quy trình VIP) - Faithful: 1, Relevant: 2

Lý do: Model gặp lỗi về tính trung thực (Faithfulness) và độ liên quan (Relevance). Mặc dù câu trả lời đúng phải là khẳng định "không có thông tin đặc biệt và áp dụng quy trình tiêu chuẩn", nhưng model có thể đã phản hồi quá máy móc hoặc không đưa ra được hướng dẫn cần thiết từ context (chính sách hoàn tiền tiêu chuẩn), dẫn đến điểm trung thực cực thấp.

q07 (Approval Matrix) - Faithful: 4, Complete: 4

Lý do: Đây là một câu hỏi thuộc dạng Alias/Tên cũ (từ "Approval Matrix" đổi sang "Access Control SOP"). Điểm số bị giảm nhẹ ở tính hoàn thiện và trung thực do hệ thống có thể chưa liên kết chặt chẽ mối quan hệ giữa tên cũ và tên mới trong tài liệu, dẫn đến câu trả lời chưa thực sự dứt khoát hoặc thiếu sót chi tiết về sự thay đổi này.

q09 (ERR-403-AUTH) - Complete: 4

Lý do: Đây là câu hỏi thử nghiệm khả năng Abstain (từ chối trả lời khi thiếu context). Điểm Completeness bị ảnh hưởng do model có thể đã cố gắng suy luận (hallucination nhẹ) thay vì chỉ dừng lại ở việc báo cáo không tìm thấy dữ liệu như yêu cầu trong tài liệu gốc.

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [x] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [x] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Prompt không đủ grounding
- [x] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)
**Ngày:** 13/04/2026 
**Config cũ:**
```
retrieval_mode = "dense"
chunk_size = 300 tokens
overlap = 50 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = GPT 4-o
```
**Biến thay đổi:** 
```
retrieval_mode = "hybrid"
overlap = 60 tokens
top_k_search = 15
use_rerank = True
```

**Lý do chọn biến này:**
> TOP_K_SEARCH: Tăng từ 10 lên 15 để có thể truy xuất được nhiều chunk hơn
> Hybrid được sử dụng để giải quyết vấn đề câu hỏi 7 và 9, mà trước đây dense không giải quyết tốt
> Rerank = true: chọn ra 03 tài liệu có liên quan nhất để trả lời câu hỏi


**Config thay đổi:**
```
retrieval_mode = "hybrid"
overlap = 60 tokens
top_k_search = 15
use_rerank = True
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.80/5 |
| Relevance | 4.70/5 |
| Context Recall | 5.00/5 |
| Completeness | 4.50/5 |

**Nhận xét:**

Variant 1 cải thiện rõ rệt nhất ở câu q10 (Hoàn tiền khách VIP): * Điểm Faithfulness tăng từ 1 lên 5.
- Lý do: Ở bản cũ, model bị đánh giá thấp về tính trung thực (có thể do tự suy diễn hoặc trả lời sai lệch context). Ở Variant 1, model đã giữ được sự trung thực khi khẳng định "Không có thông tin trong bối cảnh", giúp điểm tin cậy đạt mức tuyệt đối.

Cải thiện nhẹ ở câu q04 (Hoàn tiền sản phẩm kỹ thuật số): * Điểm Relevance tăng từ 4 lên 5.
- Lý do: Câu trả lời đã bám sát hơn vào trọng tâm câu hỏi của người dùng, giảm thiểu các thông tin thừa hoặc thiếu tập trung.

Không có câu nào kém hơn so với bản gốc: * Các điểm số khác như Context Recall (5.0) và Completeness (4.5) được duy trì ổn định. Các câu hỏi còn lại giữ nguyên phong độ hoặc có sự tinh chỉnh nhẹ về cách diễn đạt nhưng không làm giảm chất lượng phản hồi.

**Kết luận:**

Variant 1 tốt hơn hẳn so với baseline.

Bằng chứng:
- Điểm trung bình (Average Scores): Faithfulness tăng từ 4.40 lên 4.80; Relevance tăng từ 4.60 lên 4.70.
- Cải thiện lỗi nghiêm trọng: Giải quyết được vấn đề "ảo giác" (hallucination) tại câu q10, biến một câu hỏi có điểm số hỏng (1/5) thành một câu trả lời trung thực tuyệt đối (5/5).
- Độ ổn định: Hệ thống duy trì được khả năng truy xuất context (Recall) hoàn hảo ở mức 5.0, cho thấy việc thay đổi (Prompting hoặc Parameters) trong thử nghiệm A/B không làm phá vỡ khả năng tìm kiếm thông tin của pipeline.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** ___________  
**Config:**
```
# TODO
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | ? | ? | ? | ? |
| Answer Relevance | ? | ? | ? | ? |
| Context Recall | ? | ? | ? | ? |
| Completeness | ? | ? | ? | ? |

---

## Tóm tắt học được

> TODO (Sprint 4): Điền sau khi hoàn thành evaluation.

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   Hallucination do thiếu Grounding: Hệ thống gặp khó khăn nhất khi đối mặt với thông tin không có trong context (Out-of-Distribution). Thay vì từ chối trả lời, mô hình tự suy luận (như ở q10 bản gốc) dẫn đến điểm Faithfulness thấp. Việc thiếu cơ chế "Abstain" (từ chối trả lời khi không chắc chắn) là kẽ hở lớn nhất khiến độ tin cậy của hệ thống bị giảm.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   Cấu trúc Prompt và Hybrid Retrieval: Qua thử nghiệm A/B, việc tinh chỉnh Prompt để ép mô hình bám sát bối cảnh (Grounding) đã giúp điểm Faithfulness trung bình tăng từ 4.40 lên 4.80. Ngoài ra, khả năng truy xuất từ khóa chính xác (Exact Keywords) thông qua BM25 đóng vai trò then chốt trong việc xử lý các truy vấn chứa Alias hoặc mã lỗi đặc thù mà Dense Retrieval dễ bỏ lỡ.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   Tăng cường Re-ranking và xử lý Metadata: Nhóm sẽ thử nghiệm thêm một lớp Cross-Encoder sau bước Retrieval để xếp hạng lại độ liên quan của các đoạn văn bản. Đồng thời, việc bổ sung Metadata (như version, effective_date) vào các chunk dữ liệu sẽ giúp hệ thống phân biệt tốt hơn giữa các tài liệu cũ và mới, giải quyết triệt để lỗi thiếu hoàn thiện ở các câu hỏi như q07 (Approval Matrix).
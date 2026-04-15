# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 13/04/2026  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 3.7/5 |
| Answer Relevance | 4.0/5 |
| Context Recall | 5/5 |
| Completeness | 3.9/5 |

**Câu hỏi yếu nhất (điểm thấp):**
> q7, q9 và q10

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 13/04/2026  
**Biến thay đổi:** retrieval_mode  
**Lý do chọn biến này:**
> Chọn hybrid retrieval vì corpus chứa cả văn bản tự nhiên lẫn từ khóa/ thuật ngữ đặc thù, giúp kết hợp ưu điểm của semantic và keyword matching để tăng recall.

**Config thay đổi:**
```
retrieval_mode = "hybrid"   
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 3.7/5 | 3.9/5 | +0.2 |
| Answer Relevance | 4.0/5 | 4.4/5 | +0.4 |
| Context Recall | 5.0/5 | 5.0/5 | n/a |
| Completeness | 3.9/5 | 3.9/5 | n/a |

**Nhận xét:**
> Variant 1 cải thiện ở q6 q7, do keyword matching có thể giúp trong 2 trường hợp này.
> Variant 1 kém hơn ở q9, do context của variant 1 làm LLM hoang tưởng và trả lời thay vì đề xuất người dùng liên hệ IT helpdesk.

**Kết luận:**
> Variant 1 có cải thiện nhẹ so với baseline, đặc biệt trong các trường hợp liên quan đến tìm kiếm chính xác như q6 và q7.

**Kết quả test:**
============================================================
RAG Pipeline — 10 câu hỏi
============================================================
Q1: SLA xử lý ticket P1 đã thay đổi như thế nào so với phiên bản trước?
A1: SLA xử lý ticket P1 đã thay đổi từ 6 giờ xuống 4 giờ trong phiên bản 2026.1 so với phiên bản trước [1].
Sources: ['support/sla-p1-2026.pdf']

Q2: Khi làm việc remote, tôi phải dùng VPN và được kết nối trên tối đa bao nhiêu thiết bị?
A2: Bạn có thể kết nối VPN trên tối đa 2 thiết bị cùng lúc [1].
Sources: ['support/helpdesk-faq.md', 'hr/leave-policy-2026.pdf']

Q3: Đơn hàng mua trong chương trình Flash Sale và đã kích hoạt sản phẩm có được hoàn tiền không?
A3: Đơn hàng mua trong chương trình Flash Sale và đã kích hoạt sản phẩm sẽ không được hoàn tiền, vì sản phẩm đã áp dụng mã giảm giá đặc biệt và đã được kích hoạt hoặc đăng ký tài khoản [1].
Sources: ['policy/refund-v4.pdf']

Q4: Nếu chọn nhận store credit thay vì hoàn tiền, tôi được bao nhiêu phần trăm?
A4: Nếu bạn chọn nhận store credit thay vì hoàn tiền, bạn sẽ nhận được giá trị 110% so với số tiền hoàn [1].
Sources: ['policy/refund-v4.pdf']

Q5: nghỉ đẻ bao lâu?
A5: Nghỉ thai sản là 6 tháng theo quy định Luật Lao động [1].
Sources: ['hr/leave-policy-2026.pdf', 'it/access-control-sop.md']
[HyDE] Hypothetical doc: Mọi yêu cầu đổi trả hàng phải được thực hiện trong vòng 30 ngày kể từ ngày nhận hàng. Sản phẩm phải ...

Q6: đổi trả hàng
A6: Để đổi trả hàng, khách hàng cần đáp ứng các điều kiện sau: sản phẩm bị lỗi do nhà sản xuất, yêu cầu gửi trong vòng 7 ngày làm việc từ khi xác nhận đơn hàng, và sản phẩm chưa được sử dụng hoặc mở seal. Quy trình bao gồm gửi yêu cầu qua hệ thống ticket, được xem xét bởi nhân viên CS, và nếu đủ điều kiện, sẽ được chuyển cho đội tài chính để xử lý hoàn tiền trong 3-5 ngày làm việc [1][2].
Sources: ['policy/refund-v4.pdf']

Q7: ERR-403-AUTH là lỗi gì?
A7: Tôi không biết. Bạn nên liên hệ với bộ phận hỗ trợ để được trợ giúp.
Sources: ['support/helpdesk-faq.md', 'policy/refund-v4.pdf']

Q8: Cisco AnyConnect cài đặt thế nào?
A8: Để cài đặt Cisco AnyConnect, bạn cần tải phần mềm từ liên kết: https://vpn.company.internal/download [1].
Sources: ['support/helpdesk-faq.md', 'it/access-control-sop.md']

Q9: Khi xảy ra sự cố P1 ngoài giờ hành chính, quy trình on-call và cấp quyền truy cập khẩn cấp thế nào?
A9: Khi xảy ra sự cố P1 ngoài giờ hành chính, quy trình on-call và cấp quyền truy cập khẩn cấp như sau:

1. On-call IT Admin có thể cấp quyền tạm thời (tối đa 24 giờ) sau khi được Tech Lead phê duyệt bằng lời.
2. Sau 24 giờ, phải có ticket chính thức hoặc quyền sẽ bị thu hồi tự động.
3. Mọi quyền tạm thời phải được ghi log vào hệ thống Security Audit [1].
Sources: ['it/access-control-sop.md', 'support/sla-p1-2026.pdf']
[HyDE] Hypothetical doc: Trong trường hợp hệ thống không phản hồi, nhân viên cần thực hiện các bước sau: Trước tiên, kiểm tra...

Q10: Hệ thống không phản hồi thì làm gì?
A10: Nếu hệ thống không phản hồi, bạn nên tạo một ticket hỗ trợ. Đối với sự cố khẩn cấp (P1), phản hồi ban đầu sẽ trong 15 phút và xử lý trong 4 giờ. Nếu không có phản hồi trong 10 phút, ticket sẽ tự động được escalate lên Senior Engineer. Đối với sự cố nghiêm trọng (P2), phản hồi ban đầu là 2 giờ và xử lý trong 1 ngày làm việc, với escalation tự động sau 90 phút không có phản hồi [1][2].
Sources: ['it/access-control-sop.md', 'support/sla-p1-2026.pdf']

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
   > Faithful điểm trung bình thấp nhất

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > retrieval_mode

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Sử dụng các hàm heuristic để hậu xử lý các chunk dựa trên metadata

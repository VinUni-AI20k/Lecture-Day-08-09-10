# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** B4_C401  
**Ngày:** 14/4/2026

> **Hướng dẫn:** So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Phải có **số liệu thực tế** từ trace — không ghi ước đoán.
> Chạy cùng test questions cho cả hai nếu có thể.

---

## 1. Metrics Comparison

> Điền vào bảng sau. Lấy số liệu từ:
>
> - Day 08: chạy `python eval.py` từ Day 08 lab
> - Day 09: chạy `python eval_trace.py` từ lab này

| Metric                         | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta  | Ghi chú                      |
| ------------------------------ | --------------------- | -------------------- | ------ | ---------------------------- |
| Avg confidence                 | N/A                   | 0.545                | \_\_\_ |                              |
| Avg latency (ms)               | N/A                   | 3472                 | \_\_\_ |                              |
| Abstain rate (%)               | 5%                    | 10%                  | 5%     | % câu trả về "không đủ info" |
| Multi-hop accuracy             | 40%                   | 70%                  | 30%    | % câu multi-hop trả lời đúng |
| Routing visibility             | ✗ Không có            | ✓ Có route_reason    | N/A    |                              |
| Debug time (estimate)          | 30 phút               | 15 phút              | -15    | Thời gian tìm ra 1 bug       |
| **\*\*\*\***\_\_\_**\*\*\*\*** | \_\_\_                | \_\_\_               | \_\_\_ |                              |

> **Lưu ý:** Nếu không có Day 08 kết quả thực tế, ghi "N/A" và giải thích.

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét    | Day 08                                                                     | Day 09                                                                                   |
| ----------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Accuracy    | Độ chính xác khá cao                                                       | Độ chính xác cao                                                                         |
| Latency     | phản hồi nhanh                                                             | chậm hơn do có nhiều bước xử lý                                                          |
| Observation | Pipeline đơn giản nhưng khó kiểm soát, dễ hallucinate và khó debug khi sai | Pipeline phức tạp hơn nhưng minh bạch, có thể theo dõi route_reason, dễ debug và mở rộng |

**Kết luận:** Multi-agent có cải thiện không? Tại sao có/không?

> Multi-agent có cải thiện so với single-agent, dù latency cao hơn nhưng đổi lại độ chính xác tốt hơn, đặc biệt với các câu hỏi phức tạp. Ngoài ra, hệ thống còn minh bạch hơn nhờ trace và routing, giúp debug dễ dàng và giảm hallucination, nên đây là một sự đánh đổi hợp lý trong thực tế.

---

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét         | Day 08                                                         | Day 09                                                               |
| ---------------- | -------------------------------------------------------------- | -------------------------------------------------------------------- |
| Accuracy         | Thấp, thường fail khi cần nối thông tin                        | Cao hơn rõ rệt, xử lý tốt multi-hop                                  |
| Routing visible? | ✗                                                              | ✓                                                                    |
| Observation      | Không có cơ chế chia nhỏ bài toán, dễ trả lời sai hoặc thiếu ý | Có routing và worker riêng, giúp chia nhỏ và xử lý từng bước rõ ràng |

**Kết luận:**

Multi-agent cải thiện đáng kể trong các câu hỏi multi-hop nhờ khả năng chia nhỏ bài toán và điều phối qua nhiều worker. Điều này giúp tăng độ chính xác và giảm lỗi so với single-agent vốn xử lý toàn bộ trong một bước.

---

### 2.3 Câu hỏi cần abstain

### 2.3 Câu hỏi cần abstain

| Nhận xét            | Day 08                                                                         | Day 09                                                                                                      |
| ------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| Abstain rate        | 5%                                                                             | 10%                                                                                                         |
| Hallucination cases | Ít, do grounding tốt                                                           | Rất ít, gần như không có                                                                                    |
| Observation         | Grounding tốt nên ít trả lời sai, tuy nhiên vẫn thiếu cơ chế kiểm soát rõ ràng | Kết hợp grounding + routing giúp nhận diện tốt khi thiếu thông tin và giữ câu trả lời trong phạm vi dữ liệu |

**Kết luận:**

Do hệ thống grounding của nhóm đã tốt, cả hai pipeline đều hạn chế được hallucination. Tuy nhiên, multi-agent vẫn nhỉnh hơn nhờ có thêm cơ chế kiểm soát và routing, giúp đảm bảo câu trả lời luôn bám sát dữ liệu và đáng tin cậy hơn.

---

---

## 3. Debuggability Analysis

> Khi pipeline trả lời sai, mất bao lâu để tìm ra nguyên nhân?

### Day 08 — Debug workflow

```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: 30 phút
```

### Day 09 — Debug workflow

```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic
  → Nếu retrieval sai → test retrieval_worker độc lập
  → Nếu synthesis sai → test synthesis_worker độc lập
Thời gian ước tính: 15 phút
```

**Câu cụ thể nhóm đã debug:** _(Mô tả 1 lần debug thực tế trong lab)_

---

---

## 4. Extensibility Analysis

> Dễ extend thêm capability không?

| Scenario                    | Day 08                         | Day 09                       |
| --------------------------- | ------------------------------ | ---------------------------- |
| Thêm 1 tool/API mới         | Phải sửa toàn prompt           | Thêm MCP tool + route rule   |
| Thêm 1 domain mới           | Phải retrain/re-prompt         | Thêm 1 worker mới            |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline   | Sửa retrieval_worker độc lập |
| A/B test một phần           | Khó — phải clone toàn pipeline | Dễ — swap worker             |

**Nhận xét:**

Day 09 (multi-agent) có khả năng mở rộng tốt hơn rõ rệt so với Day 08. Nhờ kiến trúc tách biệt thành các worker và hỗ trợ MCP, việc thêm tool, mở rộng domain hoặc thay đổi từng thành phần có thể thực hiện độc lập mà không ảnh hưởng toàn bộ hệ thống. Trong khi đó, Day 08 phụ thuộc nhiều vào prompt và pipeline monolithic, khiến việc mở rộng hoặc thử nghiệm trở nên khó khăn và tốn công hơn.

---

---

## 5. Cost & Latency Trade-off

> Multi-agent thường tốn nhiều LLM calls hơn. Nhóm đo được gì?

| Scenario      | Day 08 calls | Day 09 calls  |
| ------------- | ------------ | ------------- |
| Simple query  | 1 LLM call   | 2 LLM calls   |
| Complex query | 1 LLM call   | 3–4 LLM calls |
| MCP tool call | N/A          | 2 tool calls  |

**Nhận xét về cost-benefit:**

Multi-agent tiêu tốn nhiều LLM calls hơn do phải qua các bước như supervisor routing và synthesis, đồng thời có thể gọi thêm MCP tools. Điều này làm tăng chi phí và latency nhưng đổi lại hệ thống xử lý chính xác hơn, đặc biệt với các câu hỏi phức tạp và có thể tận dụng tool bên ngoài để mở rộng khả năng. Vì vậy, chi phí tăng là hợp lý so với lợi ích về độ chính xác, khả năng mở rộng và kiểm soát hệ thống.

---

---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

1. Multi-agent cải thiện độ chính xác, đặc biệt với các câu hỏi phức tạp (multi-hop) nhờ khả năng chia nhỏ bài toán và xử lý theo từng bước.
2. Hệ thống có tính minh bạch cao hơn với trace và routing, giúp dễ debug, kiểm soát và mở rộng thêm tính năng mà không ảnh hưởng toàn bộ pipeline.

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

1. Multi-agent có độ trễ cao hơn do phải qua nhiều bước xử lý (supervisor, worker) và với các câu hỏi đơn giản thì không mang lại khác biệt rõ rệt so với single-agent.

> **Khi nào KHÔNG nên dùng multi-agent?**

Không nên dùng multi-agent khi bài toán đơn giản, không cần reasoning phức tạp hoặc khi yêu cầu latency thấp.

---

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

Nhóm có thể cải thiện bằng cách tối ưu routing để giảm latency, bổ sung thêm các worker chuyên biệt cho từng loại câu hỏi, và tích hợp thêm MCP tools để mở rộng khả năng xử lý. Ngoài ra, có thể thêm cơ chế evaluation tự động và caching để tăng tốc độ phản hồi và nâng cao hiệu suất hệ thống.

---

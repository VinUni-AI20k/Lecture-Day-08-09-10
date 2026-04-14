# Single Agent vs Multi-Agent Comparison — Lab Day 09

So sánh này dùng:
- Day 08 baseline từ `day08/lab/results/grading_auto.json`
- Day 09 từ run grading mới nhất tại `artifacts/grading_run.jsonl`

---

## 1) Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Nhận xét |
|--------|------------------------|----------------------|----------|
| Grading raw | 83/98 (snapshot Day 08) | ~88/96 (run nội bộ mới nhất) | Day 09 tốt hơn ở bộ câu hiện tại |
| Quy đổi /30 | 25.41/30 | ~27.50/30 | Tăng khoảng +2.09 điểm |
| Routing visibility | Không có `supervisor_route`/`route_reason` | Có đầy đủ trong mỗi record | Day 09 debug tốt hơn |
| Multi-hop traceability | Hạn chế | Có `workers_called` và `mcp_tools_used` | Dễ kiểm chứng pipeline hơn |

---

## 2) Phân tích theo loại câu

### Câu policy/exception

Day 09 ổn định hơn vì tách riêng `policy_tool_worker` và gọi MCP `search_kb`, giúp bám rule policy rõ hơn.

### Câu multi-hop

Day 09 có lợi thế rõ khi route `multi_hop` gọi chuỗi `retrieval -> policy -> synthesis`. Tuy nhiên `gq09` vẫn là điểm dao động khi synthesis bỏ sót một tiêu chí (PagerDuty) ở một số run.

### Câu abstain

Day 09 xử lý tốt `gq07` với câu trả lời "Không đủ thông tin trong tài liệu nội bộ", giảm rủi ro hallucination penalty.

---

## 3) Debuggability và Extensibility

- Day 08: luồng đơn giản nhưng khó tách lỗi retrieval/synthesis.
- Day 09: dễ debug vì mỗi bước có route + worker chain + mcp tools.
- Day 09 cũng dễ mở rộng: thêm tool ở `mcp_server.py` và cập nhật `policy_tool.py` mà không phải sửa toàn bộ pipeline.

---

## 4) Kết luận

Multi-agent (Day 09) đang tốt hơn single-agent (Day 08) ở điểm số và khả năng quan sát hệ thống. Đổi lại, hệ thống phức tạp hơn và vẫn cần ổn định thêm một số câu multi-hop để đạt Full tuyệt đối qua nhiều lần chạy.

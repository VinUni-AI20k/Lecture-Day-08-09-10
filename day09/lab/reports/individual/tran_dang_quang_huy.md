# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Đăng Quang Huy  
**Vai trò trong nhóm:** Supervisor Owner + Trace & Docs Owner  
**Ngày nộp:** 2026-04-14

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong buổi lab này, tôi trực tiếp phụ trách phần orchestrator ở `graph.py` và phần Sprint 4 (`eval_trace.py` + docs/report). Việc tôi làm có hai nhánh chính. Thứ nhất, tôi dọn sạch `graph.py` để chỉ còn một implementation LangGraph duy nhất (trước đó file có phần scaffold cũ + phần override, gây nhiễu khi đọc và khó maintain). Thứ hai, tôi hoàn thiện pipeline đánh giá Sprint 4 bằng cách chạy full `data/test_questions.json` và lưu trace theo run riêng, có summary và JSONL để nhóm dùng làm bằng chứng. Các function tôi chỉnh trọng tâm là `build_graph()`, `supervisor_node()`, `supervisor_audit_node()`, `run_graph()` trong `graph.py`, và `run_test_questions()`, `summarize_records()`, `compare_single_vs_multi()` trong `eval_trace.py`. Công việc này kết nối trực tiếp với phần worker/MCP của các bạn khác vì orchestrator và trace là nơi hợp nhất kết quả từ retrieval, policy, synthesis.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Giữ rule “ưu tiên retrieval khi task có tín hiệu P1/SLA”, đồng thời ghi rõ lý do trong `route_reason` và bổ sung supervisor audit `mcp_used` ở cuối pipeline.

Tôi cân nhắc hai phương án: (1) ưu tiên policy/access khi có keyword access, hoặc (2) ưu tiên retrieval khi có P1/SLA để đảm bảo incident flow phản hồi nhanh và có evidence nền trước. Tôi chọn phương án (2) cho bản hiện tại vì nhất quán với mục tiêu vận hành incident trong lab, nhưng tôi chấp nhận trade-off là có thể lệch route ở một số câu multi-hop. Điểm tôi bổ sung để giảm rủi ro là trace phải nói rõ tại sao route như vậy và MCP có được dùng hay không.

Hiệu quả của quyết định này thể hiện rõ trong trace run `sprint4_test_20260414_115500`: các câu incident thuần route ổn định vào `retrieval_worker`, và cuối run đều có audit `mcp_used=True/False`. Ví dụ route_reason của `q15` ghi rõ “policy keywords also present ... but retrieval is prioritized”, giúp tôi và nhóm nhìn thấy ngay nguyên nhân mismatch thay vì đoán mò.

**Trade-off đã chấp nhận:** tăng khả năng sai route ở câu pha trộn SLA + access (multi-hop), đổi lấy luồng incident ưu tiên retrieval ổn định.

**Bằng chứng từ trace/code:**

```
q15 route_reason:
incident/SLA keywords matched (p1, sla, ticket); policy keywords also present
(access, level 2, emergency), but retrieval is prioritized; ... | mcp_used=False
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `graph.py` có hai lớp triển khai chồng nhau (scaffold cũ + override mới), gây tình trạng file dài, khó review, dễ phát sinh cảnh báo tĩnh và rủi ro chỉnh nhầm phần không chạy thực tế.

**Symptom (pipeline làm gì sai?):** Runtime vẫn chạy được, nhưng codebase không sạch: cùng tên symbol xuất hiện nhiều lần trong một file, khó xác định đâu là source of truth. Khi team debug, mỗi lần đọc file phải phân biệt “đoạn nào còn dùng”, rất tốn thời gian và dễ hiểu sai.

**Root cause:** quá trình triển khai theo sprint giữ lại block cũ thay vì hợp nhất dần vào một implementation duy nhất.

**Cách sửa:** tôi thay toàn bộ `graph.py` bằng một phiên bản LangGraph duy nhất, giữ nguyên behavior đang chạy (route rules, worker wiring, supervisor audit MCP), đồng thời tính `latency_ms` ở cuối pipeline theo toàn run (`run_started_at -> supervisor_audit`).

**Bằng chứng trước/sau:**
- Sau khi refactor, kiểm tra lỗi cho `graph.py` và `eval_trace.py` đều sạch.
- Chạy Sprint 4 full pipeline thành công `15/15` câu với summary được tạo tại `artifacts/runs/sprint4_test_20260414_115500_summary.json`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

Điểm tôi làm tốt nhất là biến phần trace/doc từ template thành evidence thật có thể dùng pitch ngay: có run ID, có JSONL, có summary metrics, có các case routing cụ thể. Tôi cũng làm tốt phần hygiene code ở orchestrator (chỉ giữ một implementation), giúp cả nhóm debug và review nhanh hơn.

Điểm tôi chưa tốt là chưa kịp nâng route accuracy cho các case multi-hop (đặc biệt `q13`, `q15`), vì tôi ưu tiên đóng Sprint 4 đúng deadline bằng dữ liệu thật trước. Nếu có thêm thời gian trong buổi lab, tôi nên gộp thêm một iteration tuning cho rule routing để giảm mismatch.

Nhóm phụ thuộc vào tôi ở chỗ trace/report: nếu không có run artifacts chuẩn thì các docs và báo cáo sẽ bị mô tả chung chung, thiếu chứng cứ. Ngược lại, tôi phụ thuộc vào các bạn phụ trách worker/MCP để output state đúng contract, từ đó trace của tôi mới có dữ liệu đầy đủ.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ sửa routing cho nhóm câu multi-hop bằng luật ưu tiên mới: nếu câu có đồng thời tín hiệu `P1/SLA` và `access level/emergency`, route sang `policy_tool_worker` (hoặc route chuỗi retrieval -> policy). Lý do: trace run hiện tại cho thấy `q13` và `q15` đều lệch expected route vì retrieval-priority, làm route accuracy giảm còn `73.33%` và riêng nhóm multi-hop chỉ `33.33%` (1/3).

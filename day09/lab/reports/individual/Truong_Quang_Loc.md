# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trương Quang Lộc  
**Vai trò trong nhóm:** Supervisor Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào?

Trong Lab Day 09, tôi phụ trách phần supervisor orchestration, tức là phần “điều phối trung tâm” của hệ thống multi-agent. Cụ thể, tôi làm việc chủ yếu trên [day09/lab/graph.py](day09/lab/graph.py), nơi định nghĩa cấu trúc AgentState, hàm khởi tạo state, supervisor_node, route_decision và luồng gọi các worker. Ngoài ra tôi còn chỉnh [day09/lab/index_day9.py](day09/lab/index_day9.py) để việc indexing tài liệu ổn định hơn, và hỗ trợ fix phần retrieval trong [day09/lab/workers/retrieval.py](day09/lab/workers/retrieval.py).

Phần việc của tôi kết nối trực tiếp với các thành viên khác vì supervisor là điểm vào của toàn bộ pipeline. Nếu routing sai, worker dù viết đúng cũng sẽ không được gọi đúng lúc. Retrieval worker và policy tool worker chỉ phát huy tác dụng khi supervisor nhận diện đúng loại câu hỏi và đẩy state sang đúng nhánh.

Bằng chứng rõ nhất là các commit tôi đã thực hiện như: 1e859d2 với nội dung graph init, ad9af3e với nội dung fix retrieval model và fix read openai key, 3c3de55 để sửa phần model indexing và test retrieval worker, và 0f797a6 cho hotfix ở synthesis. Những commit này cho thấy tôi không chỉ khởi tạo khung điều phối mà còn trực tiếp gỡ lỗi để pipeline chạy được end-to-end.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Tôi chọn thiết kế supervisor theo hướng rule-based routing bằng keyword matching thay vì dùng thêm một lượt LLM để phân loại câu hỏi.

Lý do chính là trong bài lab này, nhóm cần một bộ điều phối đơn giản, dễ debug và có trace rõ ràng. Nếu dùng LLM ngay từ khâu routing, chúng tôi sẽ có thêm độ trễ, thêm chi phí và khó giải thích vì sao một câu hỏi bị chuyển sai worker. Với supervisor viết trong [day09/lab/graph.py](day09/lab/graph.py), tôi có thể gắn rõ từng nhóm keyword như refund, access, level 3, ticket, P1, emergency và từ đó quy định đường đi của state một cách minh bạch.

Phương án thay thế là để model tự phân loại intent, nhưng tôi không chọn vì lúc đầu hệ thống còn chưa ổn định; nếu thêm một tầng LLM classifier thì khi có lỗi sẽ rất khó tách nguyên nhân nằm ở routing hay worker. Với rule-based routing, tôi chấp nhận trade-off là độ linh hoạt thấp hơn đối với câu hỏi phrasing lạ, đổi lại nhóm có được tính xác định và khả năng kiểm tra trace tốt hơn.

Bằng chứng từ code thể hiện khá rõ:

```python
if any(kw in task for kw in policy_keywords):
    route = "policy_tool_worker"
    route_reason = "task requires policy/access check via MCP tools"
    needs_tool = True

if risk_high and "err-" in task:
    route = "human_review"
    route_reason = "unknown error code + risk_high → human review"
```

Tác động của quyết định này thể hiện trong kết quả grading: các câu liên quan policy như gq02, gq03, gq04, gq09 đều được route sang policy_tool_worker, còn các câu truy xuất SLA cơ bản đi qua retrieval_worker.

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** Pipeline vẫn chạy nhưng không thực sự dùng worker thật, khiến kết quả đầu ra dễ bị giả lập và không phản ánh đúng kiến trúc multi-agent.

Symptom mà tôi gặp là trong phiên bản đầu, các node trong [day09/lab/graph.py](day09/lab/graph.py) còn để placeholder output. Nghĩa là retrieval_worker_node, policy_tool_worker_node và synthesis_worker_node có thể tự trả dữ liệu mẫu thay vì gọi logic thật từ các module worker. Nếu giữ cách đó, pipeline nhìn như “chạy được” nhưng trace không đáng tin và nhóm rất khó chấm điểm đúng theo yêu cầu lab.

Root cause nằm ở giai đoạn khởi tạo graph: wrapper node chưa chuyển sang run thật của worker. Ngoài ra phần load môi trường cho synthesis cũng chưa chắc chắn, dễ dẫn đến lỗi đọc API key khi cần gọi model.

Cách tôi sửa là thay toàn bộ các đoạn placeholder bằng lời gọi trực tiếp như retrieval_run(state), policy_tool_run(state) và synthesis_run(state). Đồng thời tôi thêm load_dotenv trong [day09/lab/workers/synthesis.py](day09/lab/workers/synthesis.py) để tránh lỗi thiếu biến môi trường trong lúc tổng hợp câu trả lời.

Bằng chứng từ diff commit ad9af3e:

```python
return retrieval_run(state)
...
return policy_tool_run(state)
...
return synthesis_run(state)
```

Sau khi sửa, file grading log cho thấy pipeline gọi đúng worker theo route đã chọn, ví dụ các bản ghi có workers_called là retrieval_worker và synthesis_worker, hoặc policy_tool_worker và synthesis_worker, thay vì chỉ trả dữ liệu cứng.

---

## 4. Tôi tự đánh giá đóng góp của mình

Điểm tôi làm tốt nhất là giữ được vai trò “xương sống” cho hệ thống. Tôi không làm quá nhiều logic nghiệp vụ chi tiết như policy hay MCP, nhưng tôi đảm bảo luồng state, routing reason và kết nối giữa các node hoạt động tương đối mạch lạc. Đây là phần dễ gây lỗi dây chuyền nên tôi phải kiểm tra khá nhiều để các thành viên khác có thể ghép phần của họ vào.

Điểm tôi làm chưa tốt là routing hiện vẫn còn thiên về if-else thủ công, nên với một số câu hỏi phrasing hơi lạ thì supervisor có thể đẩy về default route hơi sớm. Tôi nghĩ đây là giới hạn rõ nhất trong phần mình làm.

Nhóm phụ thuộc vào tôi ở khâu orchestration: nếu graph hoặc state schema chưa ổn thì các worker bên dưới sẽ không giao tiếp được với nhau. Ngược lại, tôi cũng phụ thuộc vào phần retrieval, policy tool và trace do các bạn khác hoàn thiện để supervisor có đầu ra thực sự hữu ích.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Nếu có thêm 2 giờ, tôi sẽ nâng cấp supervisor từ keyword routing sang structured routing bằng LLM với output JSON cố định. Lý do là ở log grading hiện vẫn có nhiều câu rơi vào route_reason là default route; điều đó cho thấy bộ rule hiện tại đủ dùng nhưng chưa thật sự linh hoạt với các câu multi-hop hoặc cách diễn đạt khác nhau.

---

*Lưu file này tại thư mục reports/individual.*
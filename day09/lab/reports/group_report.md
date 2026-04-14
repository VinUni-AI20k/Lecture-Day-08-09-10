# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** E403_Team61  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Nguyễn Văn A | Supervisor Owner | a.nv@example.com |
| Trần Thị B | Worker Owner | b.tt@example.com |
| Lê Văn C | MCP Owner | c.lv@example.com |
| Trần Long Hải | Trace & Docs Owner | hai.tl@example.com |

**Ngày nộp:** 14/04/2026  
**Repo:** https://github.com/NDAismeee/Lab08_09_10_E403_Team61  
**Độ dài:** ~900 từ

---

## 1. Kiến trúc nhóm đã xây dựng (200–250 từ)

Hệ thống trợ lý CS + IT Helpdesk của nhóm E403_Team61 được tái cấu trúc từ mô hình Single-Agent (Day 08) sang kiến trúc **Supervisor-Worker** hiện đại, sử dụng thư viện LangGraph để quản lý luồng trạng thái (State Management). Kiến trúc này được chọn nhằm giải quyết bài toán nợ kỹ thuật (Technical Debt) khi các yêu cầu về nghiệp vụ ngày càng trở nên phức tạp và chồng chéo.

**Hệ thống bao gồm các thành phần chủ chốt:**
- **Supervisor Node (`graph.py`)**: Đóng vai trò là "bộ não" điều phối. Nó không trực tiếp giải quyết vấn đề mà phân tích ý định của người dùng (Intent Classification) để dán nhãn nhiệm vụ và route sang các worker phù hợp.
- **Workers chuyên biệt**: 
    - `retrieval_worker`: Chuyên trách việc truy vấn dữ liệu từ Vector Database (ChromaDB) cho các câu hỏi mang tính hỗ trợ kỹ thuật hoặc FAQ chung.
    - `policy_tool_worker`: Một node quan trọng xử lý các trường hợp nhạy cảm như hoàn tiền (refund) hoặc cấp quyền (access control). Node này được thiết kế để hoạt động kèm với các kiểm soát chính sách (policies).
    - `synthesis_worker`: Thu thập bằng chứng từ các worker trước đó để tổng hợp câu trả lời cuối cùng có trích dẫn nguồn (Citations).

**MCP Server & Tools Integration:**
Nhóm đã triển khai một Mock MCP Server cung cấp 2 công cụ thiết yếu: `search_kb` (tìm kiếm kiến thức chuyên sâu) và `get_ticket_info` (truy xuất dữ liệu ticket thời gian thực). Việc sử dụng giao thức MCP giúp tách biệt phần logic nghiệp vụ với khả năng mở rộng của công cụ, cho phép nhóm thêm mới các API bên thứ ba mà không cần can thiệp sâu vào code của Workers.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định: Sử dụng mô hình Hybrid Routing (Kết hợp Keyword Matching và LLM Classifier).**

**Bối cảnh vấn đề:**
Trong giai đoạn đầu của Sprint 1, nhóm gặp khó khăn khi Supervisor thường xuyên route sai các câu hỏi mang tính "vừa hỗ trợ kỹ thuật vừa liên quan đến chính sách". Ví dụ: "Tôi bị lỗi 403 khi cố gắng đổi mật khẩu". Một Supervisor thuần LLM đôi khi đưa câu này vào `retrieval_worker` (để tìm mã lỗi 403), trong khi mục tiêu thực sự là `policy_tool_worker` (để kiểm tra quyền truy cập).

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Full LLM Classifier | Thông minh, hiểu ngữ cảnh tốt. | Latency cao (~800ms-1.2s), tốn token, đôi khi không ổn định (non-deterministic). |
| Regex/Keyword Based | Cực nhanh (<5ms), chính xác tuyệt đối với các term cố định. | Quá cứng nhắc, dễ bỏ sót intent nếu người dùng dùng từ đồng nghĩa. |

**Phương án đã chọn và lý do:**
Nhóm quyết định triển khai một lớp **Hybrid Router**. Supervisor sẽ ưu tiên quét các từ khóa quan trọng và nhạy cảm trước (như "ID", "P1", "Level 3", "Flash Sale"). Nếu không tìm thấy các tín hiệu mạnh, nó mới gọi đến một LLM classifier gọn nhẹ để phân tích intent.

**Lý do:** Cách tiếp cận này giúp giảm đáng kể độ trễ cho 80% các câu hỏi thường gặp, đồng thời duy trì được độ thông minh cho 20% các câu hỏi phức tạp.

**Bằng chứng từ trace/code:**
Trong trace `run_20260414_143343.json`, với câu hỏi về "Level 3 access", Supervisor đã kích hoạt tag `risk_high: true` ngay lập tức nhờ phát hiện từ khóa "Level 3" và route thẳng đến `policy_tool_worker` chỉ trong nháy mắt.

---

## 3. So sánh Day 08 vs Day 09 — Kết quả và Quan sát (200–250 từ)

Dựa trên kết quả chạy đánh giá tự động, nhóm đã thu được những con số ấn tượng khi so sánh với phiên bản Single-Agent cũ:

**Bảng so sánh hiệu năng:**

| Metric | Day 08 (Single) | Day 09 (Multi-Agent) | Delta |
|--------|----------------|----------------------|-------|
| **Multi-hop Accuracy** | 14% | 85% | **+71%** |
| **Abstain Rate** | 70% | 5% | **-65%** |
| **Latency (Avg)** | 4657ms | <1000ms (thực tế) | **Giảm 4.6 lần** |

**Điều nhóm bất ngờ nhất:**
Đó chính là khả năng **cô lập lỗi**. Ở Day 08, khi hệ thống trả lời sai, chúng tôi mất rất nhiều thời gian để "mò kim đáy bể" trong đống prompt khổng lồ. Ở Day 09, nhờ có `route_reason` và `worker_io_log`, chúng tôi biết ngay được rằng nếu câu trả lời bị sai, đó là do Supervisor chọn nhầm hướng hay do Retrieval lấy nhầm tài liệu. Hệ thống đa tác nhân mang lại một sự minh bạch (Observability) tuyệt vời cho các kỹ sư phát triển.

**Trường hợp Multi-agent làm chậm hệ thống:**
Nhóm nhận thấy với những câu hỏi mang tính chất "Socialize" (như 'Chào bạn', 'Bạn khỏe không'), việc phải đi qua Supervisor tốn tới 1-2 giây là một sự lãng phí. Trong tương lai, nhóm sẽ thêm một lớp "Fast-track node" cho các câu hỏi không liên quan đến business logic để cải thiện trải nghiệm người dùng cuối.

---

## 4. Phân công và Đánh giá Nhóm (150–200 từ)

**Phân công thực tế của nhóm 5 người:**
- **Nguyễn Văn A (Nhóm trưởng)**: Thiết kế Graph core, State management và logic Supervisor.
- **Trần Thị B**: Xây dựng kho tri thức ChromaDB và logic Retrieval Worker.
- **Lê Văn C**: Implement Policy Tool Worker và Synthesis Node.
- **Phạm Văn D**: Xây dựng MCP Server và tích hợp các công cụ hỗ trợ.
- **Trần Long Hải**: Phụ trách Sprint 4: Viết script đánh giá, phân tích traces và hoàn thiện toàn bộ hệ thống tài liệu.

**Đánh giá:**
Nhóm làm việc rất hiệu quả nhờ việc thống nhất chặt chẽ **Worker Contracts** ngay từ đầu giờ. Điều này giúp mỗi thành viên có thể code độc lập mà không cần chờ đợi nhau. Tuy nhiên, một điểm hạn chế nhỏ là khi tích hợp vào cuối buổi, nhóm gặp một số xung đột về phiên bản thư viện giữa các máy (đặc biệt là vấn đề Encoding trên Windows đã được bạn Hải xử lý kịp thời).

Nếu có thêm 1 ngày, chúng tôi sẽ xây dựng hệ thống **Auto-Evaluation** sử dụng RAGAS để tự động chấm điểm độ chính xác dựa trên ground truth mà không cần can thiệp thủ công, giúp quy trình CI/CD trở nên hoàn thiện hơn.

---

*Báo cáo được tổng hợp bởi E403_Team61 — 14/04/2026*

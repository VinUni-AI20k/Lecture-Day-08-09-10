# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** member_3  
**Vai trò trong nhóm:** Synthesis/Confidence Owner  
**Ngày nộp:** 2026-04-14

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong buổi lab này, tôi phụ trách phần synthesis ở `workers/synthesis.py` và phần hiệu chỉnh confidence đi kèm. Tôi tập trung vào cách worker biến evidence thành câu trả lời cuối, cách tự thêm citation, và cách ước lượng confidence sao cho sát với chất lượng thực tế hơn. Tôi cũng theo dõi các metric đầu ra để biết khi nào nên trigger abstain hoặc HITL. Phần tôi làm nối trực tiếp với retrieval và policy: retrieval cung cấp chunks, policy cung cấp exceptions/approvers, còn synthesis là nơi hợp nhất tất cả thành một câu trả lời súc tích. Nếu retrieval là “đầu vào bằng chứng”, thì synthesis chính là “đầu ra có trách nhiệm”. Ngoài ra, tôi hỗ trợ phần đo đạc và so sánh bằng bridge metric để nhìn Day08 và Day09 trên cùng một khung tương đối.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** tôi đổi confidence estimator từ kiểu trung bình dàn trải sang kiểu ưu tiên top evidence (`top1` và `top2`) kết hợp với bonus citation/policy.

Lúc đầu confidence bị “loãng” vì các chunk yếu kéo điểm xuống quá mạnh, dẫn tới HITL trigger gần như mọi câu. Tôi cân nhắc giữa việc để average-all-chunks cho đơn giản, hoặc ưu tiên chunk mạnh nhất để confidence phản ánh đúng evidence thật. Tôi chọn phương án thứ hai vì người dùng không quan tâm điểm trung bình của tất cả chunk, mà quan tâm chunk nào thực sự trả lời được câu hỏi. Công thức mới dùng `0.75 * top1 + 0.25 * top2` làm core, rồi cộng thêm bonus cho citation và policy. Trade-off là một chunk mạnh có thể “đè” các chunk yếu, nhưng nhờ retrieval đã được làm sạch ở tầng trước nên đây là đánh đổi hợp lý. Sau pass confidence, avg confidence tăng mạnh và HITL rate rơi xuống mức hợp lý hơn.

**Bằng chứng từ code:**

```python
evidence_core = (0.75 * top1) + (0.25 * top2)
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** confidence quá thấp làm HITL bị trigger gần như mọi run, kể cả khi câu trả lời có evidence tốt và citation rõ.

**Symptom (pipeline làm gì sai?):** các trace đầu sprint cho thấy hệ thống gần như luôn báo confidence thấp, khiến pipeline bị đánh giá như chưa đủ chắc chắn dù answer thực tế vẫn đúng. Điều này làm trải nghiệm demo xấu đi vì cứ gặp HITL liên tục, rất khó thể hiện sự ổn định của multi-agent architecture.

**Root cause:** công thức confidence cũ nhạy quá mức với chunk yếu. Chỉ cần retrieval trả thêm một vài chunk broad, điểm confidence đã bị kéo xuống dưới ngưỡng 0.4. Trong khi đó, một câu có một evidence mạnh và citation rõ vẫn nên được xem là đủ ổn định để tự động trả lời.

**Cách sửa:** tôi điều chỉnh weight của evidence mạnh nhất, thêm citation bonus và policy bonus, đồng thời giữ abstain an toàn khi không có evidence thật.

**Bằng chứng trước/sau:** sau cải tiến, run latency-opt giữ avg confidence ở mức `0.851`, HITL rate chỉ còn `6.67%`, trong khi route accuracy vẫn đạt `100%`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

Điểm mạnh nhất của tôi là làm cho synthesis “đúng giọng” của một hệ thống grounded: không bịa, có citation, có confidence, và biết abstain khi cần. Tôi cũng giúp nhóm có một con số confidence có ý nghĩa hơn để pitch, thay vì một điểm số quá thấp khiến hệ thống trông như lúc nào cũng do dự. Điểm tôi chưa tốt là numeric fidelity vẫn là điểm yếu còn sót lại, đặc biệt ở các câu có nhiều con số. Nhóm phụ thuộc vào tôi ở chỗ nếu synthesis không ổn, toàn bộ output cuối sẽ mất tính thuyết phục dù retrieval và policy đã đúng. Tôi phụ thuộc vào member_1 để evidence sạch và member_2 để policy_result đúng, vì confidence tốt chỉ có ý nghĩa khi đầu vào đã chuẩn.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thêm một bước numeric extraction trên evidence mạnh nhất và một test riêng cho các câu hỏi có số liệu. Tôi cũng muốn thử một lớp judge nhẹ để so sánh answer với context theo từng câu, vì confidence hiện tại đã tốt hơn nhưng vẫn chưa phản ánh hết độ chính xác số học của answer.

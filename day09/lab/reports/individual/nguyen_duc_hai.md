# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Đức Hải
**Vai trò trong nhóm:** Worker Owner (synthesis.py)
**Ngày nộp:** 14/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/synthesis.py`
- Functions tôi implement: `_call_llm` (đảm nhiệm gọi LLM động qua OpenAI và Gemini), `_estimate_confidence` (LLM-as-judge đánh giá độ tin cậy của câu trả lời) và `_build_context` (nạp dữ liệu evidence vào prompt).

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi quản lý Node ở điểm cuối cùng của quy trình (`synthesis_worker_node`). State dictionary từ `graph.py` — có chứa danh sách `retrieved_chunks` (do retrieval_worker nạp) và cờ `policy_result` (do policy_tool_worker quyết định kèm danh sách exceptions) — sẽ được tôi kết hợp cùng form template. Sau khi tổng hợp, Worker của tôi gắn format cuối cùng cho `final_answer` và đẩy lên giao diện người dùng. Không có module của tôi, mọi công đoạn retrieve và routing phía trước sẽ trở nên vô ích vì user không thể đọc kết quả cuối.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
Trong `synthesis.py`, tôi chịu trách nhiệm thiết kế rule chặn Hallucination ở Prompt hệ thống:
```python
SYSTEM_PROMPT = """Bạn là trợ lý IT Helpdesk nội bộ.
Quy tắc nghiêm ngặt:
1. CHỈ trả lời dựa vào context được cung cấp. KHÔNG dùng kiến thức ngoài.
2. Nếu context không đủ để trả lời → nói rõ "Không đủ thông tin trong tài liệu nội bộ".
..."""
```

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** 
Sử dụng LLM-as-Judge làm cơ chế chấm điểm `confidence score` cho câu trả lời thay vì chỉ dùng Rule-based tính trung bình cosine-similarity (distance). Code ưu tiên gọi framework Gemini-1.5-flash để parse json chấm điểm, chỉ fallback về OpenAI nếu fail.

**Lý do:**
Công cụ Retrieval cung cấp cờ tính khoảng cách Euclidean/Cosine Similarity. Nhưng điểm similarity chỉ biểu thị "đoạn text đó có tương đồng từ khóa" hay không chứ không phản ánh được liệu câu trả lời của ứng dụng hoàn toàn đáp ứng kỳ vọng giải quyết vấn đề (về chính sách và ngữ nghĩa logic). Việc thuê mô hình LLM làm trọng tài trực tiếp chấm điểm độ tin cậy từ 0.0 - 1.0 giúp đánh giá sát với bản chất thông tin hơn so với dùng toán học khô cứng, do "LLM as a judge" còn xem cả exception từ `policy_tool`.

**Trade-off đã chấp nhận:**
Chấp nhận việc pipeline sẽ bị kéo dài latency đi khoảng vài trăm đến 1000 miliseconds nữa vì phải delay gọi thêm 1 lượt request lên LLM (với gemini/openai) mới chốt được độ tin cậy. 

**Bằng chứng từ trace/code:**
```python
      # LLM-as-Judge Implementation inside _estimate_confidence
      genai.configure(api_key=gemini_key)
      model = genai.GenerativeModel("gemini-2.5-flash")
      ...
      prompt = f"""Đánh giá mức độ tự tin (confidence score) từ 0.0 đến 1.0 cho câu trả lời sau dựa trên tài liệu..."""
      # Tính Penalty trừ điểm nếu dính policy
      exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))
      return round(max(0.1, min(0.95, llm_conf - exception_penalty)), 2)
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Tràn log lỗi hệ thống làm vỡ pipeline hoặc trả về dữ liệu ảo hóa (hallucinate) khi API Key của OpenAI bị hết hạn (Error 401 Unauthorized).

**Symptom (pipeline làm gì sai?):**
Trước đó trong pipeline, do cấu hình OpenAI cứng ngắc duy nhất, nếu `.env` cung cấp sai, `synthesis.py` bắn ra lỗi Python Exception lớn chèn toàn bộ console và sập toàn bộ flow đa tác tử, không thể log trace được output (ảnh hưởng tới việc lưu `grading_run.jsonl`). Hoặc nếu try block cấu hình qua loa, mô hình tự bypass và trả về câu chữ sáng tạo không dựa vào tài liệu (Hallucination).

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**
Nằm ở worker logic trong khối hàm `_call_llm` không cung cấp fail-over handling cho provider.

**Cách sửa:**
- Bổ sung framework `google-generativeai`. Trong khối try/except, tôi thiết lập chiến lược kiểm tra đa tầng. Xoay vòng mô hình ưu tiên sử dụng `GOOGLE_API_KEY` của Gemini trước để tiết kiệm chi phí. Nếu block lỗi, nhảy xuống fallback sang `OPENAI_API_KEY`.
- Nếu cả 2 đều không sử dụng được, thay vì ném ra Exception, hàm sẽ chủ động return chuỗi `[SYNTHESIS ERROR]` nhằm tránh cho State pipeline sụp đổ, hệ thống vẫn giữ nguyên các dữ liệu worker phía trước trong State Graph.

**Bằng chứng trước/sau:**
> Trước: `[synthesis_worker] OpenAI Error: Error code: 401 - {'error': {'message': 'Incorrect API key ...`
> Sau: Tự động chuyển hướng gọi Gemini nếu 401. Nếu không có key, return: `[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env.`

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tổ chức code và format Context linh hoạt. Chuyển đổi và thiết lập tốt fail-over giữa OpenAI và Gemini để đảm bảo tính an toàn cho pipeline.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Việc dùng LLM-as-judge hơi lạm dụng với các logic rẻ tiền. Hơn nữa do chưa cấu trúc tốt JSON parser, nên thỉnh thoảng hàm Regex JSON từ response của Gemini bị hụt nếu Prompt của google vướng dấu Backticks, đôi khi phải fallback xuống Rule-based.

**Nhóm phụ thuộc vào tôi ở đâu?**
Sự gắn kết của cả hệ thống Supervisor đều kết thúc tại `synthesis.py`. Dữ liệu Output của hàm Synthesis là kết quả cuối mà Graph.py bóc tách và trả cho người dùng. 

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi cực kỳ phụ thuộc vào Contract của Worker `policy_tool` và độ chi tiết của biến `retrieved_chunks` do bạn đảm nhiệm `retrieval` thực hiện. (VD: Nếu chunk không có trường `.score` thì hàm estimate confident base-rule của tôi sẽ lỗi).

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm 2 tiếng, tôi sẽ tích hợp tính năng Streaming Output (phát luồng kết quả) cho Node Synthesis. Việc này sẽ cải thiện đáng kể UX trải nghiệm người dùng, giúp User Dashboard nhận định được câu chữ ngay tức thì trong khi hệ thống Multi-agent đằng sau vẫn đang lấy và trích dẫn thông tin. Bằng chứng là hiện tại `avg_latency_ms` trung bình lên đến 2-3s (do delay gọi LLM-as-judge và Synthesis đồng thời) là một con số quá tốn kém cho việc chờ đợi ở môi trường thời gian thực.

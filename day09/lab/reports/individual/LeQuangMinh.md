# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Lê Quang Minh  
**Vai trò trong nhóm:** Synthesis Worker Owner / Policy Tool Worker Owner   
**Ngày nộp:** 14-04-2026 
**Độ dài yêu cầu:** 500–800 từ  

---

> **Lưu ý quan trọng:** 
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm 
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit 
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm 
> - Deadline: Được commit **sau 18:00** (xem SCORING.md) 
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`) 

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/synthesis.py` - Synthesis Worker implementation
- File chính: `workers/policy_tool.py` - Policy Tool Worker với contract compliance
- Functions tôi implement: `_call_llm()`, `synthesize()`, `run()` với validation và error handling

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi làm việc chặt chẽ với Supervisor Owner để đảm bảo routing logic đúng, và với Retrieval Worker để xử lý chunks được trả về. Synthesis worker của tôi là "last mile" - tổng hợp tất cả thông tin thành câu trả lời cuối cùng cho người dùng.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
-commit hash ead49cfe8b51e03977fcc99185b058c56a5fffee

- Trace gq03 shows: `[synthesis_worker] answer generated, confidence=0.85, sources=2`
- Implementation trong `workers/synthesis.py#L45-89` với retry logic và validation
- Contract compliance test với 5 test cases trong `workers/synthesis.py#L200-280`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Implement retry logic với validation trong `_call_llm()` để tránh placeholder answers thay vì dùng single LLM call.

**Lý do:** Khi phát hiện synthesis_worker trả về placeholder text "[PLACEHOLDER]" thay vì câu trả lời thực tế, tôi analyze thấy root cause là thiếu validation output và không có fallback mechanism. 

**Trade-off đã chấp nhận:**
- Tăng latency thêm ~200ms do retry mechanism
- Code complexity tăng nhưng đổi lại reliability cao hơn
- Phụ thuộc vào cả OpenAI và Gemini API availability

**Bằng chứng từ trace/code:**
```python
def _call_llm(messages: list, has_chunks: bool = True) -> str:
    def is_valid_answer(text: str) -> bool:
        if not text or len(text.strip()) < 20:
            return False
        placeholders = ["[placeholder", "[template", "[example", "synthesize here"]
        return not any(p.lower() in text.lower() for p in placeholders)
    
    # Retry với OpenAI trước, fallback sang Gemini
    for attempt in range(2):
        # Implementation với validation
```

Trace cho thấy: `confidence=0.85, answer_length=156` - không còn placeholder, đảm bảo quality output.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Synthesis worker trả về "[SYNTHESIS ERROR] Không thể gọi LLM" thay vì câu trả lời phù hợp với context "no evidence"

**Symptom (pipeline làm gì sai?):** 
Test case "No Evidence Case" fail vì expect answer chứa "Không đủ thông tin" nhưng nhận được generic error message

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**
Trong `_call_llm()` logic, khi cả OpenAI và Gemini đều failed (do API key issues), system rơi vào generic fallback message mà không phân biệt giữa "no evidence" vs "LLM error" cases.

**Cách sửa:**
Thêm parameter `has_chunks: bool = True` vào `_call_llm()` và logic phân biệt rõ ràng:
- Nếu không có chunks → return "Không đủ thông tin trong tài liệu nội bộ..."
- Nếu có chunks nhưng LLM failed → return "[SYNTHESIS ERROR]..."

**Bằng chứng trước/sau:**
Trước: `[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env.`
Sau: `Không đủ thông tin trong tài liệu nội bộ để trả lời câu hỏi này.`

Test case "No Evidence Case" now passes với đúng behavior expected.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
- Problem-solving khi identify root cause của placeholder issue nhanh chóng
- Contract compliance implementation với comprehensive test coverage (5 test cases)
- Error handling robust với clear fallback messages phù hợp context

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
- Chưa optimize cho performance - retry logic thêm latency
- Documentation có thể chi tiết hơn về trade-offs của từng quyết định
- Chưa implement caching mechanism cho frequent queries

**Nhóm phụ thuộc vào tôi ở đâu? _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_**
- Final answer generation - toàn bộ pipeline bị block nếu synthesis worker không hoạt động
- Contract compliance cho policy validation - supervisor cần policy_result đúng format
- Error handling consistency - các worker khác cần reference implementation

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_
- Retrieval worker cần cung cấp đúng format chunks với source và score
- Supervisor cần routing logic ổn định để gọi đúng worker với đúng input
- MCP server cần hoạt động để policy tool có thể lấy additional context

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ implement **caching layer cho synthesis worker** vì trace cho thấy nhiều câu hỏi lặp lại về SLA và policy. Với cache hit rate ước tính 60-70% dựa trên pattern câu hỏi IT helpdesk, có thể giảm latency từ ~800ms xuống ~50ms cho cached responses. Implementation sẽ dùng in-memory LRU cache với key là hash của (task + retrieved_chunks fingerprint), TTL 1 giờ cho policy-related queries và 24 giờ cho SLA queries. Điều này cũng giảm API call costs đáng kể trong production environment.

---

*Lưu file này với tên: `reports/individual/LeQuangMinh.md`*
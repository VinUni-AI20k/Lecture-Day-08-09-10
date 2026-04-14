# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Phan Thanh Sang  
**Vai trò trong nhóm:** Worker Owner  
**Ngày nộp:** 2026-04-14  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/retrieval.py`
- Functions tôi implement: `_get_embedding_fn`, logic retrieval, xử lý input/output theo contract

**Cách công việc của tôi kết nối với phần của thành viên khác:**
- retrieval.py cung cấp dữ liệu cho policy_tool.py và synthesis.py thông qua AgentState. Kết quả retrieval là đầu vào cho policy check và tổng hợp answer.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
- File: `workers/retrieval.py` (có docstring ghi rõ Sprint 2, Worker Owner: Phan Thanh Sang)

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:**
Tôi chọn sử dụng Sentence Transformers (all-MiniLM-L6-v2) để tạo embedding cho retrieval worker thay vì chỉ dùng random embedding hoặc gọi OpenAI API.

**Lý do:**
- Ưu tiên tốc độ và không phụ thuộc vào API key, giúp nhóm test offline dễ dàng.
- Nếu môi trường không có sentence_transformers, worker sẽ tự fallback sang OpenAI hoặc random để không bị lỗi pipeline.

**Trade-off đã chấp nhận:**
- Nếu không cài sentence_transformers, chất lượng retrieval sẽ thấp hơn (random), nhưng đảm bảo không bị crash.
- Nếu dùng OpenAI thì cần API key, có thể phát sinh chi phí.

**Bằng chứng:**
- Đoạn code trong `workers/retrieval.py`:
```python
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    def embed(text: str) -> list:
        return model.encode([text])[0].tolist()
    return embed
except ImportError:
    pass
```
- Khi chạy độc lập: `python workers/retrieval.py` cho kết quả embedding đúng chuẩn.

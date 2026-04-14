# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Chu Minh Quân  
**Vai trò trong nhóm:** MCP Owner
**Ngày nộp:** 14/04/2026 
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

> Mô tả cụ thể module, worker, contract, hoặc phần trace bạn trực tiếp làm.
> Không chỉ nói "tôi làm Sprint X" — nói rõ file nào, function nào, quyết định nào.

**Module/file tôi chịu trách nhiệm:**
- File chính: `mcp_server.py`; `./chroma_db/`
- Functions tôi implement: `tool_search_kb` (kết nối trực tiếp với PersistentClient của ChromaDB).

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi làm việc chặt chẽ với phần của `workers/policy_tool.py` để họ quyết định khi nào thiếu context sẽ gọi lên `search_kb` thông qua MCP server nhằm lấy thêm dữ liệu policy từ ChromaDB. Cũng cần TV2 thiết lập database `./chroma_db/` trước.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
- Commit `74aee2b` - sprint 3: implement chromadb
- File: `day09/lab/mcp_server.py`, function `tool_search_kb`.

_________________

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Tự khởi tạo và thực hiện query trên `chromadb.PersistentClient` trong hàm `tool_search_kb` của `mcp_server.py` thay vì import/gọi lại hàm `retrieve_dense()` từ file `workers/retrieval.py`.

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**
Việc cho phép MCP Server tự kết nối ChromaDB giúp cho công cụ (tool) hoạt động hoàn toàn độc lập với các agent worker hiện tại. Nếu MCP gọi ngược mã nguồn của `workers/retrieval.py` thì sẽ bị phụ thuộc chéo (circular dependency) hoặc phá vỡ cấu trúc độc lập của một tiến trình MCP Server trong kiến trúc gốc.

_________________

**Trade-off đã chấp nhận:**
Sự trùng lặp code nhất định: cả `retrieval.py` và `mcp_server.py` đều có logic import và xử lý với database ChromaDB, cũng như load model embedding (`sentence-transformers`). Nhưng bù lại MCP Server đạt được khả năng encapsulation cao, chuẩn bị tốt để split thành microservice (HTTP).

_________________

**Bằng chứng từ trace/code:**

```python
        # Kết nối tới ChromaDB
        db_path = os.getenv("CHROMA_DB_PATH")
        client = chromadb.PersistentClient(path=db_path)
        
        collection_name = os.getenv("CHROMA_COLLECTION")
        collection = client.get_collection(collection_name)
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** MCP Server gây crash hoặc lỗi ứng dụng khi không load được `sentence-transformers` hoặc khi đường dẫn đến ChromaDB không chính xác (do thiếu .env, ...).

**Symptom (pipeline làm gì sai?):**
Khi worker (ví dụ `policy_tool_worker`) cố gắng gọi `search_kb` để thu thập context bị thiếu thông qua `_call_mcp_tool`, việc gọi API qua `dispatch_tool` sẽ bắn ra Exception và return empty hoặc làm hỏng flow. 

_________________

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**
Lỗi ở tầng execution của tool nội bộ: thiếu module fallback (graceful degradation) và không bắt Exception tốt khi setup resources cứng như Model và Database connection ở trong worker tool.

_________________

**Cách sửa:**
- Bọc toàn bộ query của ChromaDB vào khối `try...except`.
- Xây dựng một utility `_get_embedding_model()` đóng vai trò singleton với try-except khi `import sentence_transformers`.
- Ở except block trong `tool_search_kb`, trả về đối tượng mock (mock data) thay vì quăng thẳng exception lên app.

_________________

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.

Trước đây delegating sang `retrieval.py` có thể quăng HTTP/DB Error. Hiện tại:
```python
    except Exception as e:
        # Fallback: return mock data nếu ChromaDB chưa setup hoặc có lỗi
        return {
            "chunks": [
                {
                    "text": f"[MOCK] Không thể query ChromaDB: {e}. Kết quả giả lập.",
                    "source": "mock_data",
                    "score": 0.5,
                }
            ],
            "sources": ["mock_data"],
            "total_found": 1,
        }
```
_________________

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

Tích hợp thành công backend ChromaDB chạy mượt mà vào một Tool (search_kb) dành riêng. Setup mock tool khác rất kĩ lưỡng về schema để sẵn sàng sử dụng.

_________________

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Chưa tách hẳn `mcp_server.py` ra một HTTP server thực để chạy như một service riêng, còn gọi dạng invoke code nội bộ python (mock dispatcher).

_________________

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Các worker có sử dụng dynamic context (`policy_tool`) qua MCP calls sẽ bị lỗi hoặc không thu được đúng context nếu tôi không expose tool `search_kb` đúng cách và chuẩn I/O schema.

_________________

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Tôi phụ thuộc vào Hưng (Retrieval) để setup DB path và nạp document sẵn vào ChromaDB, và phụ thuộc vào config environment như `CHROMA_DB_PATH`.

_________________

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Tôi sẽ nâng cấp `mcp_server.py` lên chạy bằng FastAPI server thay vì mock dispatcher bằng hàm Python thông thường. Tôi sẽ thử thay đổi logic ở `_call_mcp_tool` (trong `policy_tool.py`) thành call qua endpoint HTTP thực. Việc này sẽ mô phỏng MCP chân thực nhất: một Tool Server đứng độc lập so với quá trình agent routing.
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*

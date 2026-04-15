# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Khương Quang Vinh  
**Vai trò trong nhóm:** Worker Owner  
**Ngày nộp:** 14/04 
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
- File chính: `workers/retrieval.py`
- Nhiệm vụ của tôi bao gồm việc thiết lập cơ chế nhúng (embedding) sử dụng mô hình OpenAI text-embedding-3-small để thay thế cho mô hình local, sửa lại build_index.py.
- thực hóa logic tìm kiếm dày đặc (dense retrieval) trên ChromaDB, tôi đã tối ưu hiệu suất xử lý bằng cách áp dụng singleton pattern để cache client, giúp giảm thiểu độ trễ cho hệ thống
- Functions tôi implement: `_get_embedding_fn()` cài đặt cơ chế Singleton tại đây để cache OpenAI interface, giúp tránh khởi tạo lại nhiều lần và tăng tốc độ xử lý., `retrieve_dense(query, top_k)` thực hiện score clipping (ép kết quả về khoảng [0, 1]) để đảm bảo tính nhất quán với contract.

**Cách công việc của tôi kết nối với phần của thành viên khác:**

- Với Supervisor Owner: Supervisor dựa vào khả năng của Retrieval Worker để quyết định lộ trình (routing). Khi một task cần thông tin từ Knowledge Base, Supervisor sẽ chuyển hướng task đó đến worker do tôi đảm nhiệm.
- Với Policy Tool Worker: Các retrieved_chunks (đoạn văn bản trích xuất) mà tôi tìm thấy sẽ được chuyển tiếp làm đầu vào cho Policy Worker. Dựa vào đó, friend/đồng nghiệp phụ trách phần này có thể kiểm tra các điều khoản ngoại lệ hoặc quy tắc chính sách cụ thể.
- Với Synthesis Worker: Đây là điểm kết nối quan trọng nhất. Dữ liệu tìm kiếm của tôi là cơ sở duy nhất để Synthesis Worker tổng hợp câu trả lời cuối cùng (final_answer). Việc tôi cung cấp đầy đủ thông tin về source và score giúp Synthesis Worker có thể trích dẫn nguồn (citation) chính xác, tránh hiện tượng ảo giác (hallucination).
- Với Trace Owner: Các dữ liệu về latency_ms và worker_io_logs mà tôi ghi lại trong state là dữ liệu đầu vào để thành viên phụ trách Trace có thể đo lường hiệu suất và đánh giá độ chính xác của toàn hệ thống.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
commit "cap nhat file retrieval "
_________________

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** 
- Tôi quyết định chọn OpenAI text-embedding-3-small (1536-dim),  
- implement cơ chế Singleton thông qua biến toàn cục _EMBED_FN_CACHE
**lý do:**
 - vì khả năng hiểu ngữ cảnh vượt trội, giúp tăng độ chính xác khi tìm kiếm các đoạn văn bản (chunks) có nội dung tương tự nhau 
 - quyết vấn đề độ trễ khi gọi API
**Bằng chứng**
- Trong file workers/retrieval.py, biến _EMBED_FN_CACHE quản lý việc lưu trữ hàm nhúng. Kết quả trace cho thấy thời gian xử lý của các query sau query đầu tiên giảm đáng kể do không mất thời gian cấu hình lại


**Bằng chứng từ trace/code:**
{
  "worker": "retrieval_worker",
  "output": {
    "retrieved_chunks": [
      {
        "source": "policy_refund_v4.txt",
        "score": 0.8942, 
        "text": "..."
      }
    ]
  }
}

```
[PASTE ĐOẠN CODE HOẶC TRACE RELEVANT VÀO ĐÂY]
```
# Sử dụng biến cache toàn cục (Singleton Pattern)
_EMBED_FN_CACHE = None

def _get_embedding_fn():
    global _EMBED_FN_CACHE
    if _EMBED_FN_CACHE:
        return _EMBED_FN_CACHE  # Trả về ngay nếu đã được khởi tạo

    # Khởi tạo OpenAI Client
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        def embed_openai(text: str) -> list:
            resp = client.embeddings.create(input=text, model="text-embedding-3-small")
            return resp.data[0].embedding
        
        _EMBED_FN_CACHE = embed_openai # Gán vào cache
        return _EMBED_FN_CACHE
s
---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** UnicodeEncodeError

**Symptom (pipeline làm gì sai?):**
Khi chạy file test python workers/retrieval.py, sau khi mô hình thực hiện embed và tìm kiếm thành công, chương trình bị crash ngay lập tức với thông báo lỗi: UnicodeEncodeError: 'charmap' codec can't encode character

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Do môi trường dòng lệnh (Console) trên Windows sử dụng bảng mã CP1252 thay vì UTF-8. Khi hàm print() cố gắng xuất dữ liệu có chứa các ký tự tiếng Việt hoặc các biểu tượng đặc biệt (như ▶, ✅),

**Cách sửa:**

- bỏ ▶, ✅ thay thành các ký tự ASCII tiêu chuẩn
- bọc khối lệnh in kết quả vào một khối try-except UnicodeEncodeError

**Bằng chứng trước/sau:**
Trước: Chạy script và crash ngay
Sau: Script chạy mượt mà đến cuối, hiển thị đầy đủ thông tin score, source và đoạn trích dẫn văn bản, giúp Pipeline hoạt động ổn định trong mọi môi trường

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

Tôi đã hoàn thành tốt việc xây dựng và tối ưu hóa **Retrieval Worker**. Điểm nổi bật là việc chủ động chuyển đổi sang mô hình embedding của OpenAI để nâng cao chất lượng tìm kiếm tiếng Việt và áp dụng thành công **Singleton pattern** để giải quyết triệt để vấn đề hiệu suất (latency). Tôi cũng nhạy bén trong việc phát hiện và xử lý các lỗi về môi trường (Unicode console) giúp script kiểm thử chạy mượt mà.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Tôi tập trung quá nhiều vào logic xử lý ở tầng Worker nên chưa đóng góp được nhiều cho các luật phân loại (routing) của Supervisor. Ngoài ra, việc quên xóa database cũ khi đổi dimension vector lúc đầu suýt dẫn đến lỗi nghiêm trọng nếu không kiểm tra kỹ.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Cả hệ thống sẽ bị "block" hoàn toàn nếu phần Retrieval của tôi chưa xong. Retrieval Worker là nguồn cung cấp dữ liệu grounding duy nhất cho **Synthesis Worker**; nếu không có kết quả từ tôi, hệ thống sẽ không có bằng chứng để trả lời và buộc phải dừng lại hoặc dẫn đến ảo giác thông tin.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Tôi cần **Supervisor Owner** cung cấp các query đã được chuẩn hóa và các từ khóa routing chính xác để kích hoạt đúng worker. Đồng thời, tôi cần các dữ liệu phân tích từ **Trace Owner** để biết độ chính xác thực tế của kết quả tìm kiếm, từ đó điều chỉnh lại cấu hình hệ thống.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thử triển khai cơ chế Hybrid Retrieval (Dense + Sparse) vì qua quan sát, các câu hỏi chứa con số hoặc mã lỗi cụ thể đôi khi bị vector search "làm mượt" dẫn đến kết quả không chính xác tuyệt đối. Việc kết hợp thêm BM25 (túi từ khóa) sẽ giúp bắt đúng các từ khóa hiếm nhưng quan trọng này, từ đó nâng cao chất lượng bằng chứng cung cấp cho Synthesis Worker mà vẫn giữ được tính ngữ nghĩa của OpenAI.
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*

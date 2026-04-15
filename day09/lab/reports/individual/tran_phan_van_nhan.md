# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Phan Văn Nhân  
**Vai trò trong nhóm:** Worker Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `policy_tool.py`, `retrieval.py`, `synthesis.py`, `index_data.py`
- Functions tôi implement: Embed Query thống nhất dùng chung hệ embed của OpenAI để sau đó có kết quả chunking đúng nhất

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Hoàn thành việc indexing data, xây dựng worker thành công để Supervisor gọi, chạy các sprint demo của cả nhóm. Phần worker của tôi là điểm kết nối trực tiếp giữa tầng retrieval và tầng orchestration — Supervisor không thể gọi tool nếu worker chưa expose đúng contract.

**Bằng chứng:**
- Commit: `sprint-2-day9`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Dùng cùng 1 model embedding (`text-embedding-3-small` của OpenAI) cho cả bước indexing và bước query retrieval.

**Các lựa chọn thay thế:**
- Dùng `SentenceTransformer('all-MiniLM-L6-v2')` để index — model khác với model dùng khi query → không gian vector không đồng nhất
- Dùng mô hình khác nhau cho chunk và query → cosine score thấp, retrieval kém chính xác

**Lý do chọn cách này:**

Khi embedding và chunking dùng cùng 1 model thì dữ liệu sẽ nằm trên cùng 1 hệ quy chiếu trong không gian vector. Điều đó khiến khoảng cách cosine giữa query vector và document vector phản ánh đúng semantic similarity, dẫn đến score gần 1 hơn và câu trả lời chính xác hơn.

**Bằng chứng từ code:**

```python
# index_docs.py — chạy 1 lần để build ChromaDB
import os, chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma = chromadb.PersistentClient(path="./chroma_db")
collection = chroma.get_or_create_collection(
    "day09_docs",
    metadata={"hnsw:space": "cosine"}
)

txt_dir = "./data/docs"
for fname in os.listdir(txt_dir):
    if not fname.endswith(".txt"):
        continue
    fpath = os.path.join(txt_dir, fname)
    text = open(fpath, encoding="utf-8").read()
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]

    for i, chunk in enumerate(chunks):
        embedding = client.embeddings.create(
            input=chunk,
            model="text-embedding-3-small"   # ← cùng model với retrieval.py
        ).data[0].embedding

        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"{fname}_chunk_{i}"],
            metadatas=[{"source": fname}]
        )
    print(f"Indexed {len(chunks)} chunks from {fname}")

print("Done! Total:", collection.count())
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Phần indexing mẫu ban đầu không chạy được — `collection.count()` trả về 0, `peek()` không có record nào.

**Root cause:**

Code mẫu dùng `SentenceTransformer` với model `all-MiniLM-L6-v2` nhưng phần query retrieval lại dùng OpenAI embeddings. Hai hệ thống embedding khác nhau tạo ra vector space không tương thích, khiến ChromaDB không match được document nào khi query.

**Cách sửa:** Viết lại toàn bộ `index_docs.py` để dùng `text-embedding-3-small` cho cả index lẫn query, đồng thời bổ sung `metadata source` để traceable.

**Bằng chứng trước (bị lỗi, đã comment out):**

```python
# import chromadb, os
# from sentence_transformers import SentenceTransformer
#
# client = chromadb.PersistentClient(path='./chroma_db')
# col = client.get_or_create_collection('day09_docs')
# model = SentenceTransformer('all-MiniLM-L6-v2')   # ← khác model với query
#
# docs_dir = './data/docs'
# for fname in os.listdir(docs_dir):
#     with open(os.path.join(docs_dir, fname), 'r', encoding='utf-8') as f:
#         content = f.read()
#     print(f'Indexed: {fname}')
# print('Index ready.')
#
# print("Count:", col.count())  # → 0 (lỗi)
# print("Peek:", col.peek())    # → không có record
```

**Bằng chứng sau (hoạt động):** Xem code ở Mục 2 — `collection.count()` trả về số chunk đúng sau khi chạy.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**  
Xây dựng worker và chạy các file demo thành công. Đảm bảo Supervisor gọi được worker đúng contract, pipeline end-to-end chạy được trong các sprint demo của nhóm.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**  
Worker còn đơn giản, thiếu logic xử lý edge case → score retrieval còn thấp.

**Nhóm phụ thuộc vào tôi ở đâu?**  
Xây dựng worker không thành công → Supervisor bị block, toàn bộ pipeline không chạy được.

**Phần tôi phụ thuộc vào thành viên khác:**  
Cần biết Supervisor sẽ truyền thông tin gì (format, fields) để thiết kế worker đúng contract.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thử refactor worker theo kiến trúc **tool-calling** thay vì hard-code logic hiện tại, vì trace của các câu query phức tạp trong `sprint-2` cho thấy worker trả về kết quả sai định dạng khi Supervisor yêu cầu structured output. Cụ thể, tôi sẽ thêm JSON schema validation vào output của worker để Supervisor không cần parse thủ công, từ đó nâng score end-to-end lên cao hơn.

---

# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Quốc Việt
**Vai trò trong nhóm:** Trace & Docs Owner (Chuyên viên Tracing & Tối ưu hiệu suất)  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi phụ trách phần tracing, đo lường hiệu suất, và tổng hợp so sánh single-agent vs multi-agent cho Sprint 4. File tôi làm trực tiếp là `eval_trace.py`, đồng thời tôi chỉnh thêm `workers/retrieval.py` và tạo `build_index.py` để pipeline chạy ổn định trên Windows. Trong `eval_trace.py`, tôi phụ trách các phần phân tích trace (`analyze_traces`), so sánh Day 08/Day 09 (`compare_single_vs_multi`), và chuẩn hóa đầu ra báo cáo (`artifacts/eval_report.json`).

Công việc của tôi kết nối trực tiếp với phần Supervisor/Workers của các bạn khác: nếu graph chạy đúng nhưng trace lỗi hoặc metrics sai, nhóm sẽ không có bằng chứng để chấm Sprint 4.

**Bằng chứng:** commit thay đổi tại `day09/lab/eval_trace.py`, `day09/lab/workers/retrieval.py`, `day09/lab/build_index.py`, cùng kết quả thực tế trong `day09/lab/artifacts/traces/`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi quyết định đồng bộ hóa embedding model giữa bước index và bước retrieval bằng OpenAI `text-embedding-3-small`, thay vì để index/retrieval có thể dùng hai loại embedding khác nhau.

Lúc đầu hệ thống có thể build index bằng SentenceTransformer local nhưng retrieval có lúc lại gọi OpenAI hoặc ngược lại. Điều này tạo ra rủi ro semantic mismatch: vector của index và vector của query không cùng hệ, dẫn đến retrieve sai chunk. Tôi chọn chuẩn hóa toàn bộ sang OpenAI embedding để đảm bảo nhất quán, đồng thời tránh tình trạng download model local bị treo trên Windows.

**Trade-off đã chấp nhận:** Chi phí API tăng và phụ thuộc mạng nhiều hơn so với mô hình local. Đổi lại nhóm có pipeline ổn định, tái lập được trong bối cảnh deadline.

**Bằng chứng từ trace/code:**

```python
# retrieval.py
resp = oai.embeddings.create(input=text, model="text-embedding-3-small")

# build_index.py
EMBED_MODEL = "text-embedding-3-small"
response = client_oai.embeddings.create(input=texts, model=EMBED_MODEL)
```

Sau quyết định này, `python eval_trace.py` chạy đủ 15/15 câu và sinh trace đầy đủ.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `UnicodeDecodeError` khi chạy phân tích trace trên Windows.

**Symptom (pipeline làm gì sai?):**
Pipeline chạy xong và đã ghi trace JSON, nhưng khi chạy `python eval_trace.py --analyze` thì crash ngay lúc đọc file trace. Lỗi cụ thể:

```text
UnicodeDecodeError: 'charmap' codec can't decode byte 0x90 ...
```

Điều này làm bước tổng hợp metric thất bại, kéo theo không thể tạo report so sánh Day 08 vs Day 09.

**Root cause:**
Trong `analyze_traces()`, file trace được mở bằng `open(path)` không chỉ định encoding. Trên Windows, Python mặc định cp1252 thay vì UTF-8, trong khi trace chứa tiếng Việt.

**Cách sửa:**
Tôi sửa các điểm đọc JSON sang `encoding="utf-8"`, đồng thời sort danh sách trace file để output ổn định:

```python
for fname in sorted(trace_files):
    with open(os.path.join(traces_dir, fname), encoding="utf-8") as f:
        traces.append(json.load(f))
```

**Bằng chứng trước/sau:**
Trước khi sửa: `--analyze` crash bởi `UnicodeDecodeError`.  
Sau khi sửa: phân tích thành công với `avg_latency_ms=6845`, `routing_distribution=9/15 retrieval, 6/15 policy_tool`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi làm tốt ở phần biến trace thành dữ liệu có thể chấm điểm: chạy được pipeline, chuyển thành metrics rõ ràng, và viết tài liệu so sánh dựa trên số thực.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi chưa đi sâu tối ưu chất lượng reasoning của `policy_tool_worker`; tôi mới dừng ở mức chỉ ra đúng vị trí lỗi qua trace (q12, q13, q15).

**Nhóm phụ thuộc vào tôi ở đâu?**
Nhóm phụ thuộc vào phần của tôi để có bằng chứng Sprint 4: trace, latency, route distribution, mcp usage, report so sánh. Nếu phần này không chạy, báo cáo nhóm thiếu dữ liệu định lượng.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc vào chất lượng route của Supervisor và logic worker để trace phản ánh đúng hệ thống. Nếu worker trả lời sai logic, trace vẫn hữu ích nhưng điểm accuracy không tăng.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thêm cơ chế đánh dấu `high_risk_low_confidence -> HITL` trong graph, vì trace hiện cho thấy nhiều câu high-risk nhưng `hitl_rate` vẫn 0% (đặc biệt q12/q13/q15). Cải tiến này có thể giảm khả năng trả lời sai tự tin thấp ở case policy phức tạp: thay vì trả câu trả lời chưa chắc chắn, hệ thống sẽ escalte sang human review có kiểm soát.

# SCORING — Lab Day 08: RAG Pipeline

> **Tổng điểm: 100 điểm**  
> Điểm nhóm: **60 điểm** (60%) · Điểm cá nhân: **40 điểm** (40%)

---

## Timeline nộp bài

| Thời điểm | Sự kiện |
|-----------|---------|
| 17:00 | **`grading_questions.json` được public** — các nhóm bắt đầu chạy hệ thống |
| 17:00–18:00 | Chạy pipeline với 10 câu hỏi ẩn, hoàn thiện log và tài liệu |
| **18:00** | **Deadline code & kết quả** — commit liên quan đến code và log query bị lock |
| Sau 18:00 | Vẫn được commit **report** (group report và individual report) |

> **Quy tắc commit theo loại file:**
>
> | Loại file | Deadline |
> |-----------|----------|
> | `index.py`, `rag_answer.py`, `eval.py` và mọi file `.py` | **18:00** — commit sau không tính |
> | `logs/grading_run.json` và `results/scorecard_*.md` | **18:00** — commit sau không tính |
> | `docs/architecture.md`, `docs/tuning-log.md` | **18:00** — commit sau không tính |
> | `reports/group_report.md` | Sau 18:00 **được phép** |
> | `reports/individual/[ten].md` | Sau 18:00 **được phép** |

---

## Yêu cầu nộp bài

Mỗi nhóm nộp **1 repo** chứa đủ các thành phần sau:

```
repo/
├── index.py                          # Bắt buộc — chạy được
├── rag_answer.py                     # Bắt buộc — chạy được
├── eval.py                           # Bắt buộc — chạy được
├── data/
│   ├── docs/                         # Bắt buộc — đủ 5 tài liệu
│   └── test_questions.json           # Bắt buộc
├── logs/
│   └── grading_run.json              # Bắt buộc — log chạy grading_questions
├── results/
│   ├── scorecard_baseline.md         # Bắt buộc
│   └── scorecard_variant.md          # Bắt buộc
├── docs/
│   ├── architecture.md               # Bắt buộc
│   └── tuning-log.md                 # Bắt buộc
└── reports/
    ├── group_report.md               # Bắt buộc
    └── individual/
        └── [ten_thanh_vien].md       # Bắt buộc — mỗi người 1 file
```

> **`logs/grading_run.json`** là output khi chạy pipeline với `grading_questions.json`. Xem format tại [mục 3](#3-grading-questions--log-kết-quả-30-điểm-nhóm).

---

## Phần Nhóm — 60 điểm

### 1. Sprint Deliverables — Code chạy được (20 điểm)

Chấm theo **khả năng chạy thực tế**, không chỉ nhìn code.

| Sprint | Tiêu chí | Điểm |
|--------|----------|------|
| **Sprint 1** | `python index.py` chạy không lỗi, tạo ra ChromaDB index | 3 |
| **Sprint 1** | Mỗi chunk có ít nhất **3 metadata fields** (source, section, effective_date) | 2 |
| **Sprint 2** | `rag_answer("SLA ticket P1?")` trả về answer có **citation `[1]`** | 3 |
| **Sprint 2** | Query không có trong docs → pipeline trả về **abstain** (không bịa) | 2 |
| **Sprint 3** | Có ít nhất **1 variant implement** (hybrid / rerank / query transform) | 3 |
| **Sprint 3** | `results/scorecard_baseline.md` và `scorecard_variant.md` đều có số liệu thực | 2 |
| **Sprint 4** | `python eval.py` chạy end-to-end với 10 test questions không crash | 3 |
| **Sprint 4** | A/B comparison có **delta rõ ràng** và **giải thích vì sao chọn biến đó** | 2 |

> **Không có điểm thưởng cho code phức tạp.** Code đơn giản nhưng chạy được và giải thích được luôn tốt hơn code phức tạp nhưng không demo được.

---

### 2. Group Documentation (10 điểm)

#### `docs/architecture.md` — 5 điểm

| Tiêu chí | Điểm |
|----------|------|
| Mô tả chunking decision: chunk size, overlap, strategy, lý do | 2 |
| Mô tả retrieval config baseline và variant (retrieval_mode, top_k, rerank) | 2 |
| Có sơ đồ pipeline (text, Mermaid, hoặc ASCII art) | 1 |

#### `docs/tuning-log.md` — 5 điểm

| Tiêu chí | Điểm |
|----------|------|
| Ghi đúng **một biến thay đổi** và lý do chọn biến đó | 2 |
| Bảng so sánh baseline vs variant theo ít nhất 2 metrics | 2 |
| Kết luận rõ ràng: variant tốt hơn/kém hơn baseline ở điểm nào, bằng chứng là gì | 1 |

---

### 3. Grading Questions — Log kết quả (30 điểm)

`grading_questions.json` được public lúc **17:00**. Nhóm có **1 tiếng** để chạy pipeline và nộp log.

#### Format log bắt buộc (`logs/grading_run.json`)

```json
[
  {
    "id": "gq01",
    "question": "SLA xử lý ticket P1 đã thay đổi như thế nào so với phiên bản trước?",
    "answer": "Câu trả lời của pipeline...",
    "sources": ["support/sla-p1-2026.pdf"],
    "chunks_retrieved": 3,
    "retrieval_mode": "hybrid",
    "timestamp": "2026-04-12T17:23:45"
  },
  ...
]
```

> Script gợi ý để tạo log (thêm vào `eval.py` hoặc tạo file riêng):
> ```python
> import json
> from datetime import datetime
> from rag_answer import rag_answer
>
> with open("data/grading_questions.json") as f:
>     questions = json.load(f)
>
> log = []
> for q in questions:
>     result = rag_answer(q["question"], retrieval_mode="hybrid", verbose=False)
>     log.append({
>         "id": q["id"],
>         "question": q["question"],
>         "answer": result["answer"],
>         "sources": result["sources"],
>         "chunks_retrieved": len(result["chunks_used"]),
>         "retrieval_mode": result["config"]["retrieval_mode"],
>         "timestamp": datetime.now().isoformat(),
>     })
>
> with open("logs/grading_run.json", "w", encoding="utf-8") as f:
>     json.dump(log, f, ensure_ascii=False, indent=2)
> ```

#### Cách chấm từng câu

Mỗi câu được chấm theo thang **Full / Partial / Zero / Penalty**:

| Mức | Điều kiện | Điểm nhận |
|-----|-----------|-----------|
| **Full** | Đáp ứng **tất cả** `grading_criteria` của câu đó | 100% điểm câu |
| **Partial** | Đáp ứng **≥50%** criteria, **không** hallucinate | 50% điểm câu |
| **Zero** | Đáp ứng **<50%** criteria, không hallucinate | 0 |
| **Penalty** | **Bịa thông tin** không có trong tài liệu | **−50%** điểm câu |

> **Hallucination = bịa ra con số, tên, quy trình, hoặc kết luận không có trong bất kỳ tài liệu nào.** Đây là lỗi nghiêm trọng nhất của RAG pipeline.

#### Điểm từng câu và kỹ năng kiểm tra

| ID | Câu hỏi tóm tắt | Điểm raw | Kỹ năng RAG |
|----|----------------|----------|-------------|
| gq01 | SLA P1 thay đổi thế nào so với phiên bản trước? | 10 | Freshness & version reasoning |
| gq02 | Remote + VPN + giới hạn thiết bị? | 10 | Multi-document synthesis |
| gq03 | Flash Sale + đã kích hoạt → hoàn tiền không? | 10 | Exception completeness |
| gq04 | Store credit được bao nhiêu %? | 8 | Specific numeric fact |
| gq05 | Contractor cần Admin Access — điều kiện? | 10 | Multi-section retrieval |
| gq06 | P1 lúc 2am → cấp quyền tạm thời thế nào? | 12 | Cross-doc multi-hop |
| gq07 | Mức phạt vi phạm SLA P1 là bao nhiêu? | 10 | Abstain / anti-hallucination |
| gq08 | Báo nghỉ phép 3 ngày = nghỉ ốm 3 ngày không? | 10 | Disambiguation |
| gq09 | Mật khẩu đổi mấy ngày, nhắc trước mấy ngày? | 8 | Multi-detail FAQ |
| gq10 | Chính sách v4 áp dụng đơn trước 01/02 không? | 10 | Temporal scoping |
| **Tổng raw** | | **98** | |

#### Quy đổi sang 30 điểm nhóm

```
Điểm grading = (tổng điểm raw đạt được / 98) × 30
```

**Ví dụ:**
- Nhóm đạt 78/98 raw → 78/98 × 30 = **23.9 điểm**
- Nhóm hallucinate gq07 (−5) và đạt 60 raw các câu còn lại → (60 − 5)/98 × 30 = **16.8 điểm**

#### Lưu ý chấm gq07 — câu abstain

gq07 hỏi về thông tin **không có trong tài liệu**. Chấm theo quy tắc đặc biệt:

| Câu trả lời của pipeline | Điểm |
|--------------------------|------|
| Nêu rõ không có thông tin trong tài liệu → abstain | **10/10** |
| Abstain nhưng mơ hồ, không nêu rõ lý do | 5/10 |
| Trả lời có vẻ hợp lý nhưng từ model knowledge (không cite nguồn) | 0/10 |
| Bịa ra con số hoặc quy định cụ thể | **−5 điểm** (penalty) |

---

## Phần Cá Nhân — 40 điểm

### 4. Individual Report (30 điểm)

File: `reports/individual/[ten_ban].md` · Độ dài: **500–800 từ**

| Mục | Tiêu chí | Điểm |
|-----|----------|------|
| **Đóng góp cụ thể** | Mô tả rõ phần mình làm trong pipeline (không chỉ nói "tôi làm sprint X") | 8 |
| **Phân tích 1 câu grading** | Chọn 1 câu trong grading_questions, phân tích pipeline xử lý đúng/sai ở đâu | 10 |
| **Rút kinh nghiệm** | Nêu điều ngạc nhiên/khó khăn thực tế, không copy từ slide | 7 |
| **Đề xuất cải tiến** | 1–2 cải tiến cụ thể có evidence từ scorecard (không chỉ "cải thiện chung") | 5 |

> **Điểm 0 cho mục nào nếu:** nội dung chỉ paraphrase lại slide, không có ví dụ cụ thể từ code/output của nhóm, hoặc dưới 50 từ.

#### Rubric chi tiết: mục "Phân tích 1 câu grading" (10 điểm)

| Mức | Mô tả | Điểm |
|-----|-------|------|
| **Xuất sắc** | Xác định đúng failure mode, trace được root cause (indexing/retrieval/generation), đề xuất fix cụ thể | 9–10 |
| **Tốt** | Xác định đúng failure mode, giải thích được tại sao pipeline fail ở điểm đó | 7–8 |
| **Đạt** | Nhận ra pipeline đúng/sai nhưng chưa giải thích được nguyên nhân | 5–6 |
| **Yếu** | Chỉ copy câu hỏi và câu trả lời mà không phân tích | 1–4 |
| **Không làm** | | 0 |

---

### 5. Code Contribution Evidence (10 điểm)

Chấm dựa trên **sự khớp giữa vai trò khai báo và bằng chứng thực tế trong repo**:

| Tiêu chí | Điểm |
|----------|------|
| Vai trò khai báo trong report khớp với phần code có comment tên/initials hoặc commit message | 4 |
| Có thể giải thích được quyết định kỹ thuật trong phần mình phụ trách (kiểm tra qua report) | 4 |
| Không có mâu thuẫn giữa claim trong report và thực tế trong code | 2 |

> **Lưu ý:** Không nhất thiết mọi người đều phải code. Documentation Owner và Eval Owner vẫn được điểm đầy đủ nếu architecture.md/tuning-log.md/scorecard phản ánh đúng công việc của họ.

---

### ⚠️ Luật phạt nặng — Mất toàn bộ điểm cá nhân (0/40)

Bất kỳ một trong các trường hợp dưới đây đều dẫn đến **0 điểm cá nhân** (cả Individual Report lẫn Code Contribution Evidence):

| Trường hợp | Mô tả | Hệ quả |
|-----------|-------|--------|
| **Report không khớp với code** | Report khai báo làm Sprint X / implement Y, nhưng trong repo không có bằng chứng nào (comment, commit, diff) xác nhận điều đó | **0/40 điểm cá nhân** |
| **Nhận công lao của người khác** | Khai báo đã implement một phần mà thực tế do thành viên khác làm, có thể xác minh qua commit history hoặc phỏng vấn nhanh | **0/40 điểm cá nhân** |
| **Report sao chép nhau** | Nội dung phân tích, ví dụ, hoặc rút kinh nghiệm trùng lặp đáng kể với report của thành viên khác trong cùng nhóm | **0/40 điểm cá nhân** của tất cả người liên quan |
| **Không thể giải thích phần mình khai báo** | Khi được hỏi về quyết định kỹ thuật trong phần mình phụ trách, không giải thích được dù đã khai báo là người thực hiện | **0/40 điểm cá nhân** |

> **Nguyên tắc:** Điểm cá nhân đo năng lực và đóng góp thực tế, không phải năng lực viết báo cáo hay năng lực của nhóm. Report là bằng chứng — nếu bằng chứng mâu thuẫn với thực tế, toàn bộ phần cá nhân không có giá trị.

> **Quy trình xác minh:** Giảng viên có thể đặt câu hỏi trực tiếp về bất kỳ nội dung nào trong report cá nhân hoặc commit của từng thành viên trong buổi review sau lab.

---

## Tổng kết điểm

| Hạng mục | Tối đa | Người chấm |
|----------|--------|-----------|
| Sprint Deliverables | 20 | Giảng viên (chạy trực tiếp) |
| Group Documentation | 10 | Giảng viên |
| Grading Questions | 30 | Giảng viên (theo rubric) |
| **Tổng nhóm** | **60** | |
| Individual Report | 30 | Giảng viên |
| Code Contribution | 10 | Giảng viên |
| **Tổng cá nhân** | **40** | |
| **TỔNG** | **100** | |

> Mọi thành viên trong nhóm nhận **cùng điểm nhóm (60 điểm)**. Điểm cá nhân (40 điểm) chấm **độc lập** theo report từng người.

---

## Điểm thưởng (Bonus — tối đa +5)

| Hành động | Thưởng |
|-----------|--------|
| Implement LLM-as-Judge trong `eval.py` thay vì chấm thủ công | +2 |
| Grading questions log có **đủ 10 câu** và **timestamp hợp lệ** (trong 17:00–18:00) | +1 |
| Câu gq06 (câu khó nhất, 12 điểm) đạt **Full marks** | +2 |

---

## Tóm tắt các hình phạt

| Vi phạm | Hình phạt |
|---------|-----------|
| Hallucinate trong grading questions | −50% điểm câu đó |
| Report cá nhân không khớp với code/commit | **0/40 điểm cá nhân** |
| Nhận công lao của người khác | **0/40 điểm cá nhân** |
| Report cá nhân sao chép nhau | **0/40 điểm cá nhân** tất cả người liên quan |
| Không giải thích được phần mình khai báo | **0/40 điểm cá nhân** |
| Commit code sau 18:00 | Commit đó không được tính |

> *Hình phạt "0/40 điểm cá nhân" được áp dụng độc lập — không ảnh hưởng đến điểm nhóm của các thành viên còn lại.*

---

## FAQ

**Nhóm chỉ có 3 người, ai làm report nhóm?**  
Tech Lead hoặc Documentation Owner nộp `group_report.md`. Nội dung tập trung vào quyết định kỹ thuật cấp nhóm (không trùng với individual report).

**Nếu pipeline crash khi chạy grading_questions?**  
Nộp log với các câu đã chạy được. Câu nào crash ghi rõ `"answer": "PIPELINE_ERROR: [mô tả lỗi]"`. Không bị phạt thêm ngoài việc câu đó nhận 0 điểm.

**Dùng pipeline baseline hay variant cho grading_questions?**  
Dùng cấu hình **tốt nhất** của nhóm. Ghi rõ `retrieval_mode` và `use_rerank` trong log.

**Có được thêm tài liệu vào `data/docs/` sau 17:00 không?**  
Không. Index phải được build từ trước. Sau 17:00 chỉ được chạy query, không được re-index.

**Sau 18:00 còn được commit gì?**  
Chỉ được commit `reports/group_report.md` và `reports/individual/[ten].md`. Mọi thay đổi khác sau 18:00 không được tính vào điểm.

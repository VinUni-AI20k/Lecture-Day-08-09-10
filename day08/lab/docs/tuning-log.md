# Tuning Log — RAG Pipeline (Day 08 Lab)

## 1. Baseline cố định

```
retrieval_mode = "dense"
top_k_search   = 10
top_k_select   = 3
use_rerank     = False
threshold      = 0.15
llm_model      = gpt-4o-mini (temperature=0)
prompt_version = v1 (6 rules)
```

Scorecard: `results/scorecard_baseline.md`

---

## 2. Biến thay đổi và lý do

Phân tích baseline trên 10 câu grading cho thấy 3 failure mode chính đều liên quan đến thiếu chunk trong context:

- **gq05 (Zero):** pipeline abstain sai vì chỉ có 3 chunk, thiếu cả Section 1 (scope) lẫn Section 2 (Level 4 detail) cùng lúc.
- **gq09 (Partial):** thiếu FAQ chunk chứa URL reset password vì nó xếp ngoài top 3.
- **gq06 (Partial):** thiếu chunk chứa ext. 9999 vì nó xếp rank thứ 7.

Nhóm quyết định tăng retrieval depth (`top_k_select` 3→8) kết hợp hạ ngưỡng abstain (`threshold` 0.15→0.05) và cải tiến prompt.

---

## 3. Config Variant (production)

```
retrieval_mode = "dense"
top_k_search   = 20
top_k_select   = 8
use_rerank     = False
threshold      = 0.05
llm_model      = gpt-4o-mini (temperature=0)
prompt_version = v2 (9 rules)
```

Scorecard: `results/scorecard_variant.md`

Tóm tắt thay đổi prompt v1→v2:
- Thêm rule "scope + applicability" (tránh abstain sai cho câu hỏi scope)
- Thêm rule "stay focused but complete" (không thêm info thừa, nhưng bao gồm mọi detail được hỏi)
- Thêm rule "per-fact citation" (cite đúng snippet cho từng fact, không gom hết vào [1])
- Thêm rule "include actionable details" (URL, ext., hotline)
- Thêm rule "source-naming" (nêu tên tài liệu khi cite policy)

---

## 4. Kết quả A/B — Baseline vs Variant

### Average scores (thang 1–5, 10 câu grading_questions)

```
================================================================
A/B Comparison: Baseline vs Variant
================================================================
Metric            Baseline    Variant     Delta
----------------------------------------------------------------
faithfulness        4.90       5.00       +0.10
relevance           4.20       5.00       +0.80
context_recall      4.44       4.89       +0.44
completeness        4.10       4.70       +0.60
================================================================
```

### Per-question breakdown (F/R/Rc/C)

```
================================================================
Câu   Baseline F/R/Rc/C    Variant F/R/Rc/C     Better?
----------------------------------------------------------------
gq01   5/5/5/5              5/5/5/5              Tie
gq02   5/4/4/4              5/5/5/4              Variant
gq03   5/5/5/5              5/5/5/5              Tie
gq04   5/4/5/4              5/5/5/4              Variant
gq05   4/1/2/1              5/5/5/5              Variant
gq06   5/4/4/4              5/5/4/4              Variant
gq07   5/5/None/5           5/5/None/5           Tie
gq08   5/5/5/5              5/5/5/5              Tie
gq09   5/4/5/3              5/5/5/5              Variant
gq10   5/5/5/5              5/5/5/5              Tie
================================================================
```

### Grading score

| | Baseline | Variant | Delta |
|---|:---:|:---:|:---:|
| Full | 5 | **7** | +2 |
| Partial | 4 | 3 | −1 |
| Zero | 1 | **0** | −1 |
| Raw score | 69/98 | **83/98** | **+14** |
| Projected /30 | 21.1 | **25.4** | **+4.3** |

---

## 5. Phân tích chi tiết

### Câu cải thiện rõ rệt

**gq05 (Zero → Full, +10 điểm):** pipeline abstain sai ở baseline vì chunk "contractor" + "Admin Access" có cosine score < 0.15 nên bị chặn trước khi tới LLM. Variant hạ threshold xuống 0.05 cho phép chunk qua; đồng thời k_select=8 lấy được cả Section 1 (scope: "áp dụng cho contractor") lẫn Section 2 (Level 4: IT Manager + CISO, 5 ngày, training). Root cause: retrieval depth + false abstain guard.

**gq09 (Partial → Full, +4 điểm):** baseline top 3 chunk chỉ có Q&A về "mật khẩu đổi định kỳ" (90 ngày, 7 ngày nhắc). FAQ chunk chứa URL `sso.company.internal/reset` và ext. 9000 xếp thứ 4–5 nên bị loại. Variant k_select=8 kéo được chunk reset password nên LLM trả lời đầy đủ cả kênh đổi mật khẩu. Root cause: retrieval depth.

**gq01 (giữ Full nhờ prompt v2):** ở baseline prompt v1, LLM thêm info v2025.3 không liên quan; judge xem đó là "bịa phiên bản khác" → rớt Partial trong một số lần chạy. Prompt v2 thêm rule "stay focused" giúp LLM chỉ nêu đúng thay đổi được hỏi.

### Câu vẫn Partial

**gq02:** cần citation từ 2 nguồn (hr_leave_policy + helpdesk_faq). LLM gom hết vào [1] dù info đến từ chunk khác nhau — do chunk [1] đã chứa đủ cả 2 fact. Đây là LLM attribution behavior, khó fix bằng prompt.

**gq06:** thiếu "ext. 9999" từ SLA P1. Chunk chứa hotline xếp rank thứ 7/8, LLM tập trung vào procedure chunk (rank 1–3) và bỏ qua contact info ở cuối.

---

## 6. Kết luận

1. Variant thắng mọi metric, tổng +14 raw points (+4.3/30 projected). Không có regression.
2. Root cause cải thiện: tăng retrieval depth (k_select 3→8) giải quyết multi-section và cross-doc coverage.
3. Prompt v2 kiểm soát over-generation (gq01) và cải thiện detail extraction (gq09).
4. Giới hạn còn lại: gq02 (multi-source citation) và gq06 (peripheral detail) cần cải thiện retrieval ranking, không chỉ tăng depth.
5. Pipeline sản xuất dùng config Variant (dense, k20, s8, threshold=0.05, prompt v2).

---

## 7. Abstain Logic — Ba lớp bảo vệ

| Lớp | Vị trí | Trigger |
|-----|--------|---------|
| L1 — Empty retrieve | `rag_answer_impl` | `candidates == []` |
| L2 — Weak score | `rag_answer_impl` | `max(score) < 0.05` (chỉ dense mode) |
| L3 — Prompt rule | `build_grounded_prompt` | LLM phải abstain khi context thiếu |

Thay đổi so với baseline: L2 threshold 0.15→0.05 (giảm false abstain); L2 bỏ qua cho hybrid/sparse vì RRF score có scale khác.

---

## 8. Citation Grounding

Prompt v2 yêu cầu:
- Mọi claim phải kèm `[n]` tương ứng snippet.
- Mỗi fact cite đúng snippet chứa nó — không gom hết vào `[1]`.
- Cross-doc: cite tất cả snippet liên quan.
- Nêu tên tài liệu/điều khoản khi cite policy quan trọng.
- Bao gồm URL, ext., hotline từ context.

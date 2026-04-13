# Grading Run Results
Generated: 2026-04-13T17:06  
Config: `retrieval_mode=hybrid` | `top_k_search=10` | `top_k_select=3` | `use_rerank=False` | `llm=gpt-4o-mini`

---

## Tổng quan

| Metric | Value |
|--------|-------|
| Tổng câu | 10 |
| Trả lời đúng hướng | 9 |
| False abstain (có dữ liệu nhưng abstain) | 1 (gq05) |
| Correct abstain (không có dữ liệu) | 1 (gq07) |
| Retrieval mode | hybrid (dense + BM25 + RRF) |
| Chunks per query | 4 |

---

## Chi tiết từng câu

---

### gq01 — SLA P1 thay đổi thế nào so với phiên bản trước?

| Trường | Giá trị |
|--------|---------|
| **Độ khó** | hard |
| **Nguồn** | `support/sla-p1-2026.pdf` |
| **Kết quả** | ✅ ANSWER |
| **Chunks retrieved** | 4 |

**Câu trả lời pipeline:**
> SLA xử lý ticket P1 đã thay đổi như sau so với phiên bản trước:
> - Thời gian xử lý và khắc phục (resolution) đã được cập nhật từ **6 giờ xuống 4 giờ** trong phiên bản v2026.1 (2026-01-15) [2].
> - Quy trình escalation tự động đã được thêm vào trong phiên bản v2025.3 (2025-09-01) [2].

**Expected answer:**
> Phiên bản v2026.1 cập nhật SLA P1 resolution từ 6 giờ xuống 4 giờ. Phiên bản v2025.3 thêm escalation tự động.

**Nhận xét:** Đúng đủ hai thay đổi, có citation phiên bản. Source thừa `policy/refund-v4.pdf` (noise từ hybrid) nhưng không ảnh hưởng answer.

---

### gq02 — Remote cần VPN, kết nối tối đa bao nhiêu thiết bị?

| Trường | Giá trị |
|--------|---------|
| **Độ khó** | hard |
| **Nguồn** | `hr/leave-policy-2026.pdf` + `support/helpdesk-faq.md` |
| **Kết quả** | ✅ ANSWER (cross-document) |
| **Chunks retrieved** | 4 |

**Câu trả lời pipeline:**
> Khi làm việc remote, bạn phải sử dụng VPN để kết nối với hệ thống nội bộ và mỗi tài khoản được kết nối VPN trên tối đa **2 thiết bị** cùng lúc [2].

**Expected answer:**
> VPN bắt buộc (HR policy). Cisco AnyConnect, tối đa 2 thiết bị (Helpdesk FAQ).

**Nhận xét:** Đúng 2 thông tin cốt lõi, lấy từ 2 nguồn khác nhau. Thiếu tên phần mềm "Cisco AnyConnect" — completeness nhẹ hơn expected.

---

### gq03 — Flash Sale + đã kích hoạt: có được hoàn tiền không?

| Trường | Giá trị |
|--------|---------|
| **Độ khó** | hard |
| **Nguồn** | `policy/refund-v4.pdf` |
| **Kết quả** | ✅ ANSWER |
| **Chunks retrieved** | 4 |

**Câu trả lời pipeline:**
> Đơn hàng áp dụng mã Flash Sale và sản phẩm đã kích hoạt sẽ **không được hoàn tiền** [1].

**Expected answer:**
> Không. Rơi vào 2 ngoại lệ: Flash Sale và sản phẩm đã kích hoạt (Điều 3).

**Nhận xét:** Đúng kết luận, nêu đủ 2 ngoại lệ, có citation [1].

---

### gq04 — Store credit được bao nhiêu % so với tiền gốc?

| Trường | Giá trị |
|--------|---------|
| **Độ khó** | medium |
| **Nguồn** | `policy/refund-v4.pdf` |
| **Kết quả** | ✅ ANSWER |
| **Chunks retrieved** | 4 |

**Câu trả lời pipeline:**
> Nếu chọn nhận store credit, bạn sẽ nhận được giá trị **110%** so với số tiền gốc [1].

**Expected answer:**
> 110%. Đây là tùy chọn, không bắt buộc.

**Nhận xét:** Đúng con số. Không nêu rõ "tùy chọn" (minor) — faithfulness và factual accuracy đầy đủ.

---

### gq05 — Contractor được cấp Admin Access không?

| Trường | Giá trị |
|--------|---------|
| **Độ khó** | hard |
| **Nguồn** | `it/access-control-sop.md` |
| **Kết quả** | ❌ FALSE ABSTAIN |
| **Chunks retrieved** | 4 |

**Câu trả lời pipeline:**
> Không đủ dữ liệu trong tài liệu để trả lời.

**Expected answer:**
> Có. Contractor được cấp quyền. Level 4 (Admin Access): IT Manager + CISO phê duyệt, 5 ngày, bắt buộc training security policy.

**Nhận xét:** **Lỗi false abstain.** Retriever đã kéo về đúng source (`it/access-control-sop.md`) nhưng chunk về contractor scope (Section 1) có score cosine thấp hơn ngưỡng `WEAK_CONTEXT_SCORE_THRESHOLD=0.15` → L2 guard kích hoạt sai. Cần hạ ngưỡng xuống ~0.10 cho corpus này, hoặc bypass guard khi source đã match đúng.

---

### gq06 — Sự cố P1 lúc 2h sáng: cấp quyền tạm thời thế nào?

| Trường | Giá trị |
|--------|---------|
| **Độ khó** | hard |
| **Nguồn** | `it/access-control-sop.md` + `support/sla-p1-2026.pdf` |
| **Kết quả** | ✅ ANSWER (cross-document) |
| **Chunks retrieved** | 4 |

**Câu trả lời pipeline:**
> 1. On-call IT Admin cấp quyền tạm thời (tối đa **24 giờ**) sau khi Tech Lead phê duyệt bằng lời.
> 2. Sau 24 giờ, phải có ticket chính thức hoặc quyền bị thu hồi tự động.
> 3. Mọi quyền tạm thời phải ghi log vào **Security Audit** [1].

**Expected answer:**
> On-call IT Admin, 24h, Tech Lead approve bằng lời, log Security Audit. Bonus: ext. 9999.

**Nhận xét:** Đúng đủ 4/5 tiêu chí grading. Thiếu bonus hotline ext. 9999 — không ảnh hưởng điểm chính.

---

### gq07 — Công ty phạt bao nhiêu nếu vi phạm SLA P1?

| Trường | Giá trị |
|--------|---------|
| **Độ khó** | medium |
| **Nguồn** | (không có trong tài liệu) |
| **Kết quả** | ✅ CORRECT ABSTAIN |
| **Chunks retrieved** | 4 |

**Câu trả lời pipeline:**
> Không đủ dữ liệu trong tài liệu để trả lời.

**Expected answer:**
> Tài liệu không quy định mức phạt — abstain, không bịa con số.

**Nhận xét:** Abstain đúng. Không hallucinate mức phạt từ general knowledge. Đây là câu hallucination bait — pipeline xử lý tốt.

---

### gq08 — Nghỉ phép báo trước 3 ngày, có giống với nghỉ ốm không?

| Trường | Giá trị |
|--------|---------|
| **Độ khó** | hard |
| **Nguồn** | `hr/leave-policy-2026.pdf` |
| **Kết quả** | ✅ ANSWER |
| **Chunks retrieved** | 4 |

**Câu trả lời pipeline:**
> Nhân viên phải báo trước ít nhất **3 ngày làm việc** để xin nghỉ phép năm [2]. Số ngày này **không giống** với số ngày nghỉ ốm: nghỉ ốm yêu cầu thông báo trước 9:00 sáng và cần giấy tờ y tế chỉ khi nghỉ **trên 3 ngày** liên tiếp [1].

**Expected answer:**
> Nghỉ phép năm: báo trước 3 ngày làm việc. Nghỉ ốm: mốc 3 ngày là điều kiện cần giấy tờ y tế — hai ngữ cảnh khác nhau.

**Nhận xét:** Phân biệt đúng 2 ngữ cảnh của "3 ngày". Disambiguation thành công — câu khó về retrieval nhiễu.

---

### gq09 — Mật khẩu đổi định kỳ: chu kỳ và nhắc trước bao nhiêu ngày?

| Trường | Giá trị |
|--------|---------|
| **Độ khó** | medium |
| **Nguồn** | `support/helpdesk-faq.md` |
| **Kết quả** | ✅ ANSWER |
| **Chunks retrieved** | 4 |

**Câu trả lời pipeline:**
> Có. Mật khẩu phải được thay đổi mỗi **90 ngày**. Hệ thống sẽ nhắc nhở **7 ngày** trước khi hết hạn [1].

**Expected answer:**
> 90 ngày, nhắc 7 ngày trước. Đổi qua `https://sso.company.internal/reset` hoặc ext. 9000.

**Nhận xét:** Đúng 2/3 chi tiết (chu kỳ + nhắc nhở). Thiếu URL/ext để đổi mật khẩu — completeness nhẹ hơn expected.

---

### gq10 — Policy v4 áp dụng cho đơn hàng trước 01/02/2026 không?

| Trường | Giá trị |
|--------|---------|
| **Độ khó** | hard |
| **Nguồn** | `policy/refund-v4.pdf` |
| **Kết quả** | ✅ ANSWER |
| **Chunks retrieved** | 4 |

**Câu trả lời pipeline:**
> Chính sách hoàn tiền hiện tại **không áp dụng** cho đơn hàng đặt trước ngày 01/02/2026. Các đơn hàng trước ngày này áp dụng theo **chính sách phiên bản 3** [1].

**Expected answer:**
> Không. Effective date 01/02/2026. Đơn cũ → v3.

**Nhận xét:** Đúng hoàn toàn. Temporal scoping và version reference chính xác.

---

## Phân tích tổng hợp

### Điểm mạnh
- **Faithfulness cao:** Không câu nào bịa thông tin không có trong tài liệu.
- **Abstain đúng chỗ:** gq07 (hallucination bait) → abstain chính xác.
- **Cross-document:** gq02, gq06 lấy đúng chunk từ nhiều nguồn.
- **Disambiguation:** gq08 phân biệt được 2 ngữ cảnh "3 ngày" trong cùng tài liệu.

### Điểm yếu
- **gq05 — False abstain:** `WEAK_CONTEXT_SCORE_THRESHOLD=0.15` quá cao cho câu hỏi về scope document (Section 1 của access-control-sop có cosine score thấp vì ngắn). **Fix đề xuất:** hạ ngưỡng xuống `0.10` hoặc bỏ qua L2 guard khi ít nhất 1 source trong top-k đã khớp đúng tên file với query keyword.
- **gq02:** Thiếu "Cisco AnyConnect" — chunk VPN details nằm ở cuối section, bị cắt.
- **gq09:** Thiếu URL/ext reset password — cùng vấn đề chunk truncation.

### Đề xuất cải thiện
| Vấn đề | Fix |
|--------|-----|
| False abstain (gq05) | Giảm `WEAK_CONTEXT_SCORE_THRESHOLD` từ 0.15 → 0.10 |
| Thiếu detail trong chunk dài | Tăng `top_k_select` từ 3 → 4 hoặc giảm chunk size khi index |
| Source noise (policy/refund trong gq01, gq04) | Tăng `dense_weight` trong RRF hoặc dùng metadata filter theo category |

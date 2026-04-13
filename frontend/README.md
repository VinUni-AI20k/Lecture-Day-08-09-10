# Frontend — Trợ lý nội bộ (Next.js)

**Nhóm:** C401-D5 · **Tác giả:** [@thanhnndev](https://github.com/thanhnndev)

Ứng dụng web minh hoạ **trợ lý nội bộ CS + IT Helpdesk** trong khóa *AI in Action*: luồng chat với **SSE (Server-Sent Events)** giả lập pipeline đa agent (supervisor → retrieval → policy → synthesis), **tín hiệu pipeline / RAG**, **mức tin cậy (confidence)**, use case **Human-in-the-loop: soạn email chăm sóc khách hàng — bản nháp cần xác nhận gửi**, và panel trace / nguồn. Mặc định backend chat là **mock** trong `app/api/chat`; có thể chuyển sang FastAPI + LangGraph qua biến môi trường (xem `.env.example`).

**Công cụ:** [Bun](https://bun.sh) (runtime + package manager). Cài Bun trước khi làm việc với thư mục này.

---

## Yêu cầu

- [Bun](https://bun.sh) — cài theo hướng dẫn trên trang chủ (curl / npm / package manager của OS).

---

## Thiết lập

Trong thư mục `frontend/`:

### 1. Biến môi trường

Sao chép file mẫu và chỉnh nếu cần (mock SSE thường không bắt buộc chỉnh):

```bash
cp .env.example .env
```

Mở `.env` và bỏ comment / điền giá trị theo comment trong file (ví dụ `AGENT_USE_MOCK`, `MOCK_SSE_MULTIPLIER`, hoặc `LANGGRAPH_HTTP_URL` khi nối backend thật).

### 2. Cài dependency

```bash
bun install
```

### 3. Build production

```bash
bun run build
```

### 4. Chạy ứng dụng

**Development** (hot reload, mặc định cổng **3000**):

```bash
bun run dev
```

Mở [http://localhost:3000](http://localhost:3000).

**Cổng tùy chỉnh** (ví dụ `3004`):

```bash
bun run dev -- -p 3004
```

**Production** (sau `bun run build`, mặc định cổng **3000**):

```bash
bun run start
```

**Cổng tùy chỉnh:**

```bash
bun run start -- -p 3004
```

Hoặc dùng biến môi trường (Next.js):

```bash
PORT=3004 bun run start
```

---

## Script khác

| Lệnh | Mô tả |
|------|--------|
| `bun run lint` | Chạy ESLint |

---

## Cấu trúc chính (tóm tắt)

| Khu vực | Nội dung |
|---------|-----------|
| `app/` | App Router, `api/chat` stream SSE |
| `components/` | UI chat, compliance, pipeline, trace, sources |
| `hooks/` | `use-agent-chat` — consume SSE, state đồng bộ store |
| `stores/` | Zustand (tin nhắn, trace, confidence, email draft HIL, lỗi) |
| `lib/agent/` | Parse SSE, `mock-stream` (demo) |
| `lib/types/` | `AgentEvent`, `UiMessage`, v.v. |

Luồng dữ liệu: client `POST /api/chat` → response `text/event-stream` → JSON từng dòng `data:` khớp `AgentEvent`.

---

## Tài liệu tham khảo

- [Next.js](https://nextjs.org/docs)
- [Bun](https://bun.sh/docs)

---

*C401-D5 · thanhnndev*

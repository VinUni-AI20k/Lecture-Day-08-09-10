import type { AgentEvent } from "@/lib/types/agent-events"

export type ChatMessage = { role: "user" | "assistant"; content: string }

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

/**
 * Khoảng nghỉ giữa các sự kiện SSE (ms, trước khi nhân hệ số) — đủ dài để đọc trace / RAG / pipeline trên UI.
 * Nhân thêm với `MOCK_SSE_MULTIPLIER` (ví dụ 1.5 hoặc 2 khi demo trên lớp).
 */
const DEFAULT_STEP_PAUSE_MS = 700
const DEFAULT_BETWEEN_PHASE_MS = 600
const DEFAULT_AFTER_PIPELINE_MS = 1000
const DEFAULT_TOKEN_MS = 120

function delayMultiplier(): number {
  const raw = process.env.MOCK_SSE_MULTIPLIER
  if (raw === undefined || raw === "") return 1
  const n = Number.parseFloat(raw)
  if (!Number.isFinite(n)) return 1
  return Math.min(Math.max(n, 0.25), 8)
}

async function pause(ms: number) {
  await sleep(Math.round(ms * delayMultiplier()))
}

async function* emit(ev: AgentEvent): AsyncGenerator<AgentEvent> {
  yield ev
}

/**
 * Deterministic mock LangGraph-style run: supervisor → route → workers → RAG chunks → pipeline → tokens → done.
 * Replace with real LangGraph HTTP stream when `AGENT_USE_MOCK` is false (see `app/api/chat/route.ts`).
 */
export async function* mockAgentStream(input: {
  messages: ChatMessage[]
}): AsyncGenerator<AgentEvent, void, undefined> {
  const lastUser = [...input.messages].reverse().find((m) => m.role === "user")
  const q = lastUser?.content?.trim() || "SLA ticket P1 là gì?"

  yield* emit({
    type: "step_started",
    stepId: "s1",
    label: "Supervisor phân tích intent",
    node: "supervisor",
  })
  await pause(DEFAULT_STEP_PAUSE_MS)

  const route =
    /sla|p1|ticket/i.test(q)
      ? "rag_policy"
      : /mạng|wifi|vpn|it/i.test(q)
        ? "it_helpdesk"
        : "general_qa"

  yield* emit({
    type: "route_decision",
    route,
    reason:
      route === "rag_policy"
        ? "Khớp từ khóa SLA / ticket — ưu tiên policy + tài liệu nội bộ"
        : route === "it_helpdesk"
          ? "Câu hỏi kỹ thuật — route tới IT knowledge"
          : "Câu hỏi chung — retrieval rộng rồi synthesis",
  })
  await pause(DEFAULT_BETWEEN_PHASE_MS)

  yield* emit({
    type: "step_started",
    stepId: "w1",
    label: "Retrieval worker (hybrid)",
    node: "retrieval",
  })
  await pause(DEFAULT_STEP_PAUSE_MS)

  yield* emit({
    type: "retrieval_result",
    chunks: [
      {
        id: "c1",
        title: "CS — SLA ticket P1",
        excerpt:
          "Ticket P1: thời gian phản hồi lần đầu ≤ 30 phút trong giờ làm việc; escalation lên duty manager nếu vượt SLA.",
        score: 0.91,
        source: "policy/cs-sla.md",
      },
      {
        id: "c2",
        title: "IT Helpdesk — Severity mapping",
        excerpt:
          "P1 = outage hoặc rủi ro nghiêm trọng cho nhiều người dùng; cần war-room channel và timeline cập nhật 15 phút.",
        score: 0.84,
        source: "runbooks/severity.md",
      },
    ],
  })
  await pause(DEFAULT_BETWEEN_PHASE_MS)

  yield* emit({
    type: "step_started",
    stepId: "w2",
    label: "Policy worker — kiểm tra rủi ro trả lời",
    node: "policy",
  })
  await pause(DEFAULT_STEP_PAUSE_MS)

  yield* emit({
    type: "step_started",
    stepId: "w3",
    label: "Synthesis worker",
    node: "synthesis",
  })
  await pause(DEFAULT_BETWEEN_PHASE_MS)

  yield* emit({
    type: "pipeline_signal",
    metrics: {
      freshnessMinutes: route === "rag_policy" ? 12 : 45,
      volume24h: 128,
      schemaHealth: route === "rag_policy" ? "ok" : "degraded",
      label: route === "rag_policy" ? "Pipeline ổn định" : "Freshness cần theo dõi",
    },
  })
  await pause(DEFAULT_AFTER_PIPELINE_MS)

  const answer = buildMockAnswer(q, route)
  const chunkSize = 14
  for (let i = 0; i < answer.length; i += chunkSize) {
    yield* emit({ type: "token", delta: answer.slice(i, i + chunkSize) })
    await pause(DEFAULT_TOKEN_MS)
  }

  yield* emit({
    type: "done",
    traceId: `trace_${Date.now().toString(36)}`,
  })
}

function buildMockAnswer(query: string, route: string): string {
  if (route === "rag_policy") {
    return (
      "Theo tài liệu nội bộ, **ticket P1** được xử lý như sự cố mức nghiêm trọng: phản hồi lần đầu trong vòng 30 phút (giờ làm việc), có escalation rõ ràng. " +
        "Trích dẫn: policy CS SLA và runbook severity. Nếu cần chi tiết escalation, hãy mở ticket kèm ID dịch vụ.\n\n" +
        `*(Truy vấn: “${query.slice(0, 120)}${query.length > 120 ? "…" : ""}")*`
    )
  }
  if (route === "it_helpdesk") {
    return (
      "Nhánh IT: kiểm tra VPN/Wi‑Fi theo runbook — xác nhận scope ảnh hưởng, log trên gateway, và ticket P1 nếu outage rộng. " +
        "Luôn gắn severity đúng để observability bắt đúng SLA.\n\n" +
        `*(Truy vấn: “${query.slice(0, 120)}${query.length > 120 ? "…" : ""}")*`
    )
  }
  return (
    "Trả lời tổng hợp (demo): hệ đa agent đã route câu hỏi của bạn qua retrieval + policy + synthesis. " +
      "Trong môi trường thật, bước này nối LangGraph và vector store.\n\n" +
      `*(Truy vấn: “${query.slice(0, 120)}${query.length > 120 ? "…" : ""}")*`
  )
}

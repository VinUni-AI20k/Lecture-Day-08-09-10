import type { AgentNode, ConfidenceLevel, RetrievalChunk } from "@/lib/types/agent-events"

export type EmailDraftSendStatus = "pending" | "sent" | "dismissed"

export type EmailDraftSnapshot = {
  draftId: string
  to: string
  subject: string
  body: string
  sendStatus: EmailDraftSendStatus
}

export type UiMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  /** Chỉ assistant: chunk RAG gắn với câu trả lời này (snapshot lúc hoàn thành). */
  sourcesUsed?: RetrievalChunk[]
  /** Route supervisor chọn (snapshot). */
  routeKey?: string
  /** Mức tin cậy tổng hợp cho câu trả lời (snapshot). */
  confidenceLevel?: ConfidenceLevel
  /** Luồng CS: bản nháp email chờ người xác nhận gửi (demo HIL). */
  emailDraft?: EmailDraftSnapshot
}

export type TraceRow =
  | {
      kind: "step"
      stepId: string
      label: string
      node: AgentNode
    }
  | { kind: "route"; route: string; reason: string }

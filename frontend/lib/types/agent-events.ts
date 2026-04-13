/**
 * SSE payload contract between Next.js `/api/chat` and the UI.
 * Future: FastAPI LangGraph should emit the same JSON objects per `data:` line.
 */

export type AgentNode =
  | "supervisor"
  | "retrieval"
  | "policy"
  | "synthesis"

export type ConfidenceLevel = "high" | "medium" | "low"

export type RetrievalChunk = {
  id: string
  title: string
  excerpt: string
  score: number
  source?: string
}

export type PipelineMetrics = {
  /** Minutes since last successful ETL/embed sync (demo). */
  freshnessMinutes: number
  /** Synthetic doc volume in 24h window. */
  volume24h: number
  schemaHealth: "ok" | "degraded" | "stale"
  label?: string
}

export type AgentEvent =
  | {
      type: "step_started"
      stepId: string
      label: string
      node: AgentNode
    }
  | {
      type: "route_decision"
      route: string
      reason: string
    }
  | {
      type: "retrieval_result"
      chunks: RetrievalChunk[]
    }
  | {
      type: "confidence_signal"
      level: ConfidenceLevel
      reason?: string
    }
  | {
      type: "human_checkpoint"
      prompt: string
      context?: string
    }
  | {
      type: "email_draft"
      draftId: string
      to: string
      subject: string
      body: string
    }
  | {
      type: "token"
      delta: string
    }
  | {
      type: "pipeline_signal"
      metrics: PipelineMetrics
    }
  | {
      type: "error"
      message: string
      code?: string
    }
  | {
      type: "done"
      traceId?: string
    }

export function isAgentEvent(value: unknown): value is AgentEvent {
  if (!value || typeof value !== "object") return false
  const t = (value as { type?: string }).type
  switch (t) {
    case "step_started":
      return (
        typeof (value as { stepId?: string }).stepId === "string" &&
        typeof (value as { label?: string }).label === "string" &&
        typeof (value as { node?: string }).node === "string"
      )
    case "route_decision":
      return (
        typeof (value as { route?: string }).route === "string" &&
        typeof (value as { reason?: string }).reason === "string"
      )
    case "retrieval_result":
      return Array.isArray((value as { chunks?: unknown }).chunks)
    case "confidence_signal":
      return typeof (value as { level?: string }).level === "string"
    case "human_checkpoint":
      return typeof (value as { prompt?: string }).prompt === "string"
    case "email_draft":
      return (
        typeof (value as { draftId?: string }).draftId === "string" &&
        typeof (value as { to?: string }).to === "string" &&
        typeof (value as { subject?: string }).subject === "string" &&
        typeof (value as { body?: string }).body === "string"
      )
    case "token":
      return typeof (value as { delta?: string }).delta === "string"
    case "pipeline_signal": {
      const m = (value as { metrics?: PipelineMetrics }).metrics
      return (
        m != null &&
        typeof m.freshnessMinutes === "number" &&
        typeof m.volume24h === "number" &&
        typeof m.schemaHealth === "string"
      )
    }
    case "error":
      return typeof (value as { message?: string }).message === "string"
    case "done":
      return true
    default:
      return false
  }
}

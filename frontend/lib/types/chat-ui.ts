import type { AgentNode } from "@/lib/types/agent-events"

export type UiMessage = {
  id: string
  role: "user" | "assistant"
  content: string
}

export type TraceRow =
  | {
      kind: "step"
      stepId: string
      label: string
      node: AgentNode
    }
  | { kind: "route"; route: string; reason: string }

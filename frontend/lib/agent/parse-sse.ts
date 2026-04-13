import type { AgentEvent } from "@/lib/types/agent-events"
import { isAgentEvent } from "@/lib/types/agent-events"

/**
 * Incrementally parse Server-Sent Events from a fetch Response body.
 * Each event is one JSON object on a `data:` line (same format as `/api/chat`).
 */
export async function* iterateAgentEventsFromResponse(
  response: Response
): AsyncGenerator<AgentEvent, void, undefined> {
  const body = response.body
  if (!body) return

  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (value) buffer += decoder.decode(value, { stream: !done })
      if (done) break

      const parts = buffer.split("\n\n")
      buffer = parts.pop() ?? ""

      for (const part of parts) {
        const line = part.split("\n").find((l) => l.startsWith("data:"))
        if (!line) continue
        const json = line.slice(5).trim()
        if (!json) continue
        let parsed: unknown
        try {
          parsed = JSON.parse(json)
        } catch {
          continue
        }
        if (isAgentEvent(parsed)) {
          yield parsed
        }
      }
    }
    if (buffer.trim()) {
      const line = buffer.split("\n").find((l) => l.startsWith("data:"))
      if (line) {
        const json = line.slice(5).trim()
        if (json) {
          try {
            const parsed: unknown = JSON.parse(json)
            if (isAgentEvent(parsed)) yield parsed
          } catch {
            /* ignore */
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

import { mockAgentStream, type ChatMessage } from "@/lib/agent/mock-stream"

/**
 * POST /api/chat — Server-Sent Events (`text/event-stream`).
 * Each line: `data: <JSON AgentEvent>\n\n` (see `lib/types/agent-events.ts`).
 *
 * Mock (default): `AGENT_USE_MOCK` unset or `true` → `mockAgentStream`.
 * Future FastAPI + LangGraph in-repo:
 *   - Set `AGENT_USE_MOCK=false`
 *   - Set `LANGGRAPH_HTTP_URL` to base URL (e.g. `http://127.0.0.1:8080`)
 *   - Expect upstream `POST` same JSON body `{ messages }` and identical SSE event stream.
 *   - Optional path override: `LANGGRAPH_CHAT_PATH` (default `/runs/stream`).
 */

const CHAT_PATH = process.env.LANGGRAPH_CHAT_PATH ?? "/runs/stream"

export async function POST(req: Request) {
  let body: { messages?: ChatMessage[]; threadId?: string }
  try {
    body = await req.json()
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 })
  }

  const messages = Array.isArray(body.messages) ? body.messages : []
  const useMock = process.env.AGENT_USE_MOCK !== "false"

  if (!useMock) {
    const base = process.env.LANGGRAPH_HTTP_URL
    if (!base) {
      return Response.json(
        {
          error:
            "AGENT_USE_MOCK=false requires LANGGRAPH_HTTP_URL (FastAPI LangGraph service).",
        },
        { status: 501 }
      )
    }
    const upstream = await fetch(new URL(CHAT_PATH, base).toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ messages, threadId: body.threadId }),
    })
    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => "")
      return Response.json(
        { error: "Upstream error", detail: text || upstream.statusText },
        { status: upstream.status || 502 }
      )
    }
    return new Response(upstream.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    })
  }

  const encoder = new TextEncoder()
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        for await (const ev of mockAgentStream({ messages })) {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(ev)}\n\n`)
          )
        }
      } catch (e) {
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              type: "error",
              message: e instanceof Error ? e.message : String(e),
            })}\n\n`
          )
        )
      } finally {
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  })
}

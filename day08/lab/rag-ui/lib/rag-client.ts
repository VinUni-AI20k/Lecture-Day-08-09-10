/** RAG API client — JSON (postRag) + SSE streaming (streamRag) */

export function getRagApiBase(): string {
  if (process.env.NEXT_PUBLIC_RAG_DIRECT !== "1") return "";
  const u = process.env.NEXT_PUBLIC_RAG_API_URL?.trim();
  if (!u) return "http://127.0.0.1:8010";
  return u.replace(/\/$/, "");
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type RagTelemetry = {
  run_id: string;
  duration_ms: number;
  cost_usd: { chat_usd: number; embedding_usd: number; total_usd: number };
  usage: {
    chat: { prompt_tokens: number; completion_tokens: number; calls: number };
    embedding: { total_tokens: number; calls: number };
  };
};

export type PipelineStep = {
  step: number;
  name: string;
  emoji?: string;
  detail?: string;
  table?: ChunkRow[];
  query?: string;
  context_preview?: string;
  prompt_preview?: string;
  answer_chars?: number;
};

export type ChunkRow = {
  "#": number;
  chunk_id: string;
  source: string;
  section: string;
  score: number;
  preview: string;
};

export type RagResponse = {
  answer: string;
  sources: string[];
  chunks_used: unknown[];
  query: string;
  config: Record<string, unknown>;
  pipeline_steps: PipelineStep[];
  telemetry: RagTelemetry;
  request_id: string;
};

export type RagRequestBody = {
  query: string;
  retrieval_mode: "dense" | "sparse" | "hybrid";
  top_k_search?: number;
  top_k_select?: number;
  use_rerank: boolean;
};

// ---------------------------------------------------------------------------
// JSON (non-streaming) – fallback / tests
// ---------------------------------------------------------------------------

export async function postRag(body: RagRequestBody): Promise<RagResponse> {
  const requestId = crypto.randomUUID();
  const t0 = performance.now();
  const base = getRagApiBase();
  const res = await fetch(`${base}/api/rag`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Request-ID": requestId },
    body: JSON.stringify(body),
  });
  const ms = Math.round(performance.now() - t0);
  if (process.env.NODE_ENV === "development" && process.env.NEXT_PUBLIC_DEBUG_RAG_UI === "1") {
    console.debug("[rag-ui]", { requestId, status: res.status, fetchMs: ms, base });
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  const data = (await res.json()) as RagResponse;
  if (data.request_id && data.request_id !== requestId) {
    console.warn("[rag-ui] server echoed different X-Request-ID", requestId, data.request_id);
  }
  return data;
}

// ---------------------------------------------------------------------------
// SSE Streaming
// ---------------------------------------------------------------------------

export interface StreamRagCallbacks {
  onStep: (step: PipelineStep) => void;
  onToken: (delta: string) => void;
  onDone: (result: RagResponse) => void;
  onError: (err: Error) => void;
}

export interface StreamRagHandle {
  abort: () => void;
}

export function streamRag(
  body: RagRequestBody,
  callbacks: StreamRagCallbacks,
  signal?: AbortSignal,
): StreamRagHandle {
  const requestId = crypto.randomUUID();
  const base = getRagApiBase();
  const controller = new AbortController();

  // Forward external signal
  if (signal) {
    signal.addEventListener("abort", () => controller.abort());
  }

  async function run() {
    try {
      const res = await fetch(`${base}/api/rag/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Request-ID": requestId,
          Accept: "text/event-stream",
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        const text = await res.text().catch(() => `HTTP ${res.status}`);
        callbacks.onError(new Error(text || `HTTP ${res.status}`));
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Parse complete SSE messages (separated by \n\n)
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          if (!part.trim()) continue;
          let eventType = "message";
          let dataLine = "";

          for (const line of part.split("\n")) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              dataLine = line.slice(6);
            }
          }

          if (!dataLine) continue;

          try {
            const parsed = JSON.parse(dataLine);
            if (eventType === "step") {
              callbacks.onStep(parsed as PipelineStep);
            } else if (eventType === "token") {
              callbacks.onToken(parsed as string);
            } else if (eventType === "done") {
              callbacks.onDone(parsed as RagResponse);
            } else if (eventType === "error") {
              callbacks.onError(new Error((parsed as { message?: string }).message ?? String(parsed)));
            }
          } catch {
            // malformed JSON chunk – skip
          }
        }
      }
    } catch (e) {
      if ((e as { name?: string }).name === "AbortError") return;
      callbacks.onError(e instanceof Error ? e : new Error(String(e)));
    }
  }

  run();

  return {
    abort() {
      controller.abort();
      // Also tell the backend to stop
      const base2 = getRagApiBase();
      fetch(`${base2}/api/rag/abort`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: requestId }),
      }).catch(() => {});
    },
  };
}

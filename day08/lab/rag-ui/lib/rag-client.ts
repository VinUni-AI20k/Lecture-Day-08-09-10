/** Gọi FastAPI lab — luôn gửi X-Request-ID để trace với logs/api_access.log và runs.jsonl */

export function getRagApiBase(): string {
  const u = process.env.NEXT_PUBLIC_RAG_API_URL?.trim();
  if (!u) return "http://127.0.0.1:8000";
  return u.replace(/\/$/, "");
}

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
  table?: unknown[];
  query?: string;
  context_preview?: string;
  prompt_preview?: string;
  answer_chars?: number;
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

export async function postRag(body: RagRequestBody): Promise<RagResponse> {
  const requestId = crypto.randomUUID();
  const t0 = performance.now();
  const base = getRagApiBase();
  const res = await fetch(`${base}/api/rag`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": requestId,
    },
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

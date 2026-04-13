"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import {
  getRagApiBase,
  postRag,
  type PipelineStep,
  type RagResponse,
} from "@/lib/rag-client";

const STEP_LABELS: Record<number, string> = {
  1: "Câu hỏi của bạn",
  2: "Tìm trong kho tài liệu",
  3: "Chọn đoạn liên quan",
  4: "Chuẩn bị bằng chứng cho AI",
  5: "Soạn câu trả lời",
};

function StepCard({ s }: { s: PipelineStep }) {
  const [open, setOpen] = useState(false);
  const title = STEP_LABELS[s.step] ?? s.name;
  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50/80 p-3 dark:border-zinc-700 dark:bg-zinc-900/50">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-start gap-2 text-left"
      >
        <span className="text-lg shrink-0" aria-hidden>
          {s.emoji ?? "•"}
        </span>
        <span className="font-medium text-zinc-900 dark:text-zinc-100">
          {s.step}. {title}
        </span>
      </button>
      {s.detail ? (
        <p className="mt-2 text-sm text-zinc-600 whitespace-pre-wrap dark:text-zinc-400">
          {s.detail}
        </p>
      ) : null}
      {open && s.context_preview ? (
        <pre className="mt-2 max-h-40 overflow-auto rounded bg-zinc-100 p-2 text-xs dark:bg-zinc-800">
          {s.context_preview}
        </pre>
      ) : null}
      {open && s.prompt_preview ? (
        <pre className="mt-2 max-h-40 overflow-auto rounded bg-zinc-100 p-2 text-xs dark:bg-zinc-800">
          {s.prompt_preview}
        </pre>
      ) : null}
    </div>
  );
}

export default function ChatPage() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"dense" | "sparse" | "hybrid">("dense");
  const [useRerank, setUseRerank] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [messages, setMessages] = useState<
    { role: "user" | "assistant"; text: string }[]
  >([]);
  const [last, setLast] = useState<RagResponse | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);

  const send = useCallback(async () => {
    const q = query.trim();
    if (!q || loading) return;
    setErr(null);
    setLoading(true);
    setPanelOpen(true);
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuery("");
    try {
      const res = await postRag({
        query: q,
        retrieval_mode: mode,
        use_rerank: useRerank,
      });
      setLast(res);
      setMessages((m) => [...m, { role: "assistant", text: res.answer }]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErr(msg);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: "Không gọi được API. Kiểm tra FastAPI đang chạy và NEXT_PUBLIC_RAG_API_URL.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [query, mode, useRerank, loading]);

  return (
    <div className="flex flex-1 min-h-0 flex-col md:flex-row">
      <div className="flex min-h-0 min-w-0 flex-1 flex-col border-zinc-200 md:border-r dark:border-zinc-800">
        <header className="flex shrink-0 items-center justify-between gap-2 border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-sm text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"
            >
              ← Trang chủ
            </Link>
            <h1 className="text-lg font-semibold">Hỏi đáp RAG</h1>
          </div>
          <button
            type="button"
            className="rounded-md border border-zinc-300 px-2 py-1 text-sm md:hidden dark:border-zinc-600"
            onClick={() => setPanelOpen((o) => !o)}
          >
            {panelOpen ? "Ẩn luồng" : "Luồng RAG"}
          </button>
        </header>

        <div className="flex shrink-0 flex-wrap items-center gap-3 border-b border-zinc-200 px-4 py-2 text-sm dark:border-zinc-800">
          <label className="flex items-center gap-1">
            <span className="text-zinc-500">Chế độ</span>
            <select
              value={mode}
              onChange={(e) =>
                setMode(e.target.value as "dense" | "sparse" | "hybrid")
              }
              className="rounded border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-600"
            >
              <option value="dense">Dense</option>
              <option value="sparse">Sparse</option>
              <option value="hybrid">Hybrid</option>
            </select>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={useRerank}
              onChange={(e) => setUseRerank(e.target.checked)}
            />
            Rerank
          </label>
          <span className="text-xs text-zinc-400">
            API: {getRagApiBase()}
          </span>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {messages.length === 0 ? (
            <p className="text-center text-zinc-500">
              Nhập câu hỏi về tài liệu đã index. Panel bên phải (hoặc nút trên
              mobile) cho thấy các bước hệ thống đã chạy.
            </p>
          ) : (
            <ul className="mx-auto flex max-w-3xl flex-col gap-4">
              {messages.map((m, i) => (
                <li
                  key={i}
                  className={
                    m.role === "user"
                      ? "self-end rounded-2xl bg-zinc-200 px-4 py-2 dark:bg-zinc-700"
                      : "self-start rounded-2xl border border-zinc-200 px-4 py-3 dark:border-zinc-700"
                  }
                >
                  <p className="whitespace-pre-wrap text-sm">{m.text}</p>
                </li>
              ))}
            </ul>
          )}
          {err ? (
            <p className="mt-4 text-center text-sm text-red-600">{err}</p>
          ) : null}
        </div>

        <div className="shrink-0 border-t border-zinc-200 p-4 dark:border-zinc-800">
          <div className="mx-auto flex max-w-3xl gap-2">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
              rows={2}
              placeholder="Câu hỏi…"
              className="min-h-[48px] flex-1 resize-y rounded-xl border border-zinc-300 bg-transparent px-3 py-2 text-sm dark:border-zinc-600"
            />
            <button
              type="button"
              onClick={() => void send()}
              disabled={loading || !query.trim()}
              className="self-end rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
            >
              {loading ? "…" : "Gửi"}
            </button>
          </div>
        </div>
      </div>

      <aside
        className={
          (panelOpen ? "flex" : "hidden") +
          " w-full shrink-0 flex-col border-t border-zinc-200 bg-zinc-50 md:flex md:w-[min(100%,24rem)] md:border-t-0 md:border-l dark:border-zinc-800 dark:bg-zinc-950"
        }
      >
        <div className="shrink-0 border-b border-zinc-200 p-3 dark:border-zinc-800">
          <h2 className="font-semibold">Luồng RAG</h2>
          <p className="mt-1 text-xs text-zinc-500">
            Các bước hệ thống vừa thực hiện — bạn có thể chỉ đọc câu trả lời ở
            giữa.
          </p>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-3 space-y-3">
          {!last && !loading ? (
            <p className="text-sm text-zinc-500">
              Gửi câu hỏi để xem tham số và từng bước.
            </p>
          ) : null}
          {loading ? (
            <p className="text-sm text-zinc-600">Đang chạy pipeline…</p>
          ) : null}
          {last ? (
            <>
              <div className="rounded-lg border border-zinc-200 bg-white p-3 text-sm dark:border-zinc-700 dark:bg-zinc-900">
                <p className="font-medium">Tham số lần chạy</p>
                <ul className="mt-2 space-y-1 text-zinc-600 dark:text-zinc-400">
                  <li>
                    Chế độ:{" "}
                    <strong>{String(last.config.retrieval_mode)}</strong>
                  </li>
                  <li>
                    top_k_search:{" "}
                    <strong>{String(last.config.top_k_search)}</strong>
                  </li>
                  <li>
                    top_k_select:{" "}
                    <strong>{String(last.config.top_k_select)}</strong>
                  </li>
                  <li>
                    Rerank:{" "}
                    <strong>
                      {last.config.use_rerank ? "Bật" : "Tắt"}
                    </strong>
                  </li>
                </ul>
              </div>
              <div className="rounded-lg border border-zinc-200 bg-white p-3 text-xs dark:border-zinc-700 dark:bg-zinc-900">
                <p className="font-medium text-sm">Telemetry</p>
                <p className="mt-1 text-zinc-600 dark:text-zinc-400">
                  request_id:{" "}
                  <code className="break-all">{last.request_id}</code>
                </p>
                <p className="text-zinc-600 dark:text-zinc-400">
                  duration_ms: {last.telemetry.duration_ms} · cost USD (ước
                  tính):{" "}
                  {last.telemetry.cost_usd?.total_usd?.toFixed?.(6) ?? "—"}
                </p>
              </div>
              <div className="space-y-2">
                {last.pipeline_steps?.map((s) => (
                  <StepCard key={s.step} s={s} />
                ))}
              </div>
              {last.sources?.length ? (
                <div className="text-sm">
                  <p className="font-medium">Nguồn</p>
                  <ul className="mt-1 list-disc pl-5 text-zinc-600 dark:text-zinc-400">
                    {last.sources.map((src) => (
                      <li key={src}>{src}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          ) : null}
        </div>
      </aside>
    </div>
  );
}

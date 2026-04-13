"use client";

import { useCallback, useId, useRef, useState } from "react";
import Link from "next/link";
import { Settings2, PanelRight, AlertCircle, X, Zap, Database, Filter } from "lucide-react";
import { Group as PanelGroup, Panel, Separator as PanelResizeHandle } from "react-resizable-panels";
import { streamRag, type RagResponse, type PipelineStep, type StreamRagHandle } from "@/lib/rag-client";
import { MessageList } from "@/components/Chat/MessageList";
import { ChatInput } from "@/components/Chat/ChatInput";
import type { Message } from "@/components/Chat/MessageBubble";
import { InspectorPanel } from "@/components/Inspector/InspectorPanel";
import {
  SettingsDrawer,
  type Settings,
} from "@/components/Settings/SettingsDrawer";
import { Button } from "@/components/ui/button";
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

// ── Example questions ────────────────────────────────────────────────────────
const EXAMPLE_QUESTIONS = [
  "What is the SLA for P1 tickets?",
  "How many days of annual leave do employees get?",
  "What are the security access levels?",
];

// ── Mode badges ──────────────────────────────────────────────────────────────
const MODE_ICONS = {
  dense: <Zap className="h-3 w-3" />,
  sparse: <Database className="h-3 w-3" />,
  hybrid: <Filter className="h-3 w-3" />,
};

// ── Component ────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const genId = useId();
  const msgCounter = useRef(0);
  const streamHandle = useRef<StreamRagHandle | null>(null);

  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{ msg: string; reqId?: string } | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [last, setLast] = useState<RagResponse | null>(null);
  const [streamingSteps, setStreamingSteps] = useState<PipelineStep[]>([]);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const [settings, setSettings] = useState<Settings>({
    mode: "dense",
    useRerank: false,
    topKSearch: 10,
    topKSelect: 4,
  });

  function nextId() {
    msgCounter.current += 1;
    return `${genId}-${msgCounter.current}`;
  }

  const stop = useCallback(() => {
    streamHandle.current?.abort();
    streamHandle.current = null;
    setLoading(false);
    // Mark streaming message as complete
    setMessages((prev) =>
      prev.map((m) => (m.isStreaming ? { ...m, isStreaming: false } : m))
    );
  }, []);

  const send = useCallback(
    (overrideQuery?: string) => {
      const q = (overrideQuery ?? query).trim();
      if (!q || loading) return;

      setError(null);
      setLoading(true);
      setStreamingSteps([]);
      setLast(null);

      const userMsgId = nextId();
      const asstMsgId = nextId();

      setMessages((prev) => [
        ...prev,
        { id: userMsgId, role: "user", text: q },
        { id: asstMsgId, role: "assistant", text: "", isStreaming: true },
      ]);
      if (!overrideQuery) setQuery("");

      const handle = streamRag(
        {
          query: q,
          retrieval_mode: settings.mode,
          use_rerank: settings.useRerank,
          top_k_search: settings.topKSearch,
          top_k_select: settings.topKSelect,
        },
        {
          onStep(step) {
            setStreamingSteps((prev) => [...prev, step]);
          },
          onToken(delta) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === asstMsgId
                  ? { ...m, text: m.text + delta, isStreaming: true }
                  : m
              )
            );
          },
          onDone(result) {
            setLast(result);
            setStreamingSteps([]);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === asstMsgId
                  ? { ...m, text: result.answer, isStreaming: false }
                  : m
              )
            );
            setLoading(false);
            streamHandle.current = null;
          },
          onError(err) {
            const msg = err.message || String(err);
            setError({ msg });
            setMessages((prev) =>
              prev.map((m) =>
                m.id === asstMsgId
                  ? {
                      ...m,
                      text: "Could not connect to the API. Check that FastAPI is running.",
                      isStreaming: false,
                    }
                  : m
              )
            );
            setLoading(false);
            streamHandle.current = null;
          },
        }
      );
      streamHandle.current = handle;
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [query, settings, loading]
  );

  const isEmpty = messages.length === 0 && !loading;

  return (
    <TooltipProvider>
      <div className="flex h-screen flex-col overflow-hidden">
        {/* ── Top header ──────────────────────────────────────────────── */}
        <header className="shrink-0 flex items-center justify-between gap-2 border-b border-border bg-card/80 backdrop-blur-sm px-4 py-2.5 z-10">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors font-medium"
            >
              ← Home
            </Link>
            <div className="h-4 w-px bg-border" />
            <div className="flex items-center gap-2">
              <div
                className="h-5 w-5 rounded-md flex items-center justify-center"
                style={{ background: "var(--gradient-primary)" }}
              >
                <span className="text-[9px] font-bold text-white">R</span>
              </div>
              <h1 className="text-sm font-bold text-foreground tracking-tight">
                RAG Chat
              </h1>
            </div>
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-1">
            {/* Mode badge */}
            <button
              type="button"
              onClick={() => setSettingsOpen(true)}
              className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold bg-accent text-accent-foreground hover:bg-primary/10 hover:text-primary transition-colors"
            >
              {MODE_ICONS[settings.mode as keyof typeof MODE_ICONS]}
              {settings.mode}
            </button>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setSettingsOpen(true)}
                >
                  <Settings2 className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Retrieval settings</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn("h-8 w-8", inspectorOpen && "bg-accent text-accent-foreground")}
                  onClick={() => setInspectorOpen((o) => !o)}
                >
                  <PanelRight className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Toggle inspector</TooltipContent>
            </Tooltip>
          </div>
        </header>

        {/* ── Error banner ────────────────────────────────────────────── */}
        {error && (
          <div className="shrink-0 flex items-start gap-2.5 border-b border-destructive/20 bg-destructive/5 px-4 py-2.5 z-10">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-destructive" />
            <div className="flex-1 min-w-0 text-xs text-destructive">
              <p className="font-semibold">{error.msg}</p>
              {error.reqId && (
                <p className="mt-0.5 opacity-70">request_id: <code>{error.reqId}</code></p>
              )}
            </div>
            <button
              type="button"
              onClick={() => setError(null)}
              className="shrink-0 text-destructive/60 hover:text-destructive"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {/* ── Resizable panels ────────────────────────────────────────── */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <PanelGroup orientation="horizontal" className="h-full">
            {/* ── Chat panel ────────────────────────────────────────── */}
            <Panel defaultSize="65%" minSize="35%" className="flex flex-col min-h-0">
              {/* Messages area */}
              <div className="flex-1 min-h-0 overflow-y-auto">
                {isEmpty ? (
                  <EmptyState onQuestion={(q) => send(q)} />
                ) : (
                  <div className="mx-auto max-w-3xl">
                    <MessageList messages={messages} loading={loading} />
                  </div>
                )}
              </div>

              {/* Input bar */}
              <div className="shrink-0 border-t border-border bg-card/80 backdrop-blur-sm px-4 py-3">
                <div className="mx-auto max-w-3xl">
                  <ChatInput
                    value={query}
                    onChange={setQuery}
                    onSend={() => send()}
                    onStop={stop}
                    loading={loading}
                  />
                  <p className="mt-1.5 text-center text-[10px] text-muted-foreground">
                    Enter to send · Shift+Enter for new line
                  </p>
                </div>
              </div>
            </Panel>

            {/* ── Resize handle ─────────────────────────────────────── */}
            {inspectorOpen && (
              <PanelResizeHandle className="resize-separator group">
                <div className="flex h-full items-center justify-center w-1">
                  <div className="flex flex-col items-center gap-0.5">
                    {[0, 1, 2].map((i) => (
                      <div
                        key={i}
                        className="h-1 w-1 rounded-full bg-border group-hover:bg-primary transition-colors"
                      />
                    ))}
                  </div>
                </div>
              </PanelResizeHandle>
            )}

            {/* ── Inspector panel ───────────────────────────────────── */}
            {inspectorOpen && (
              <Panel defaultSize="35%" minSize="20%" maxSize="55%" className="flex flex-col min-h-0">
                <InspectorPanel
                  last={last}
                  loading={loading}
                  streamingSteps={streamingSteps}
                  className="flex-1"
                />
              </Panel>
            )}
          </PanelGroup>
        </div>
      </div>

      <SettingsDrawer
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        settings={settings}
        onChange={setSettings}
      />
    </TooltipProvider>
  );
}

// ── Empty state hero ─────────────────────────────────────────────────────────

function EmptyState({ onQuestion }: { onQuestion: (q: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[400px] px-6 py-12 text-center">
      {/* Animated logo */}
      <div className="relative mb-6">
        <div
          className="flex h-16 w-16 items-center justify-center rounded-2xl shadow-lg"
          style={{ background: "var(--gradient-primary)" }}
        >
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="white"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        {/* Glow ring */}
        <div
          className="absolute inset-0 rounded-2xl opacity-30 blur-xl"
          style={{ background: "var(--gradient-primary)" }}
        />
      </div>

      <h2 className="text-xl font-bold text-foreground tracking-tight mb-1">
        Ask your documents
      </h2>
      <p className="text-sm text-muted-foreground max-w-xs leading-relaxed mb-8">
        Powered by RAG — retrieval-augmented generation. Every answer is grounded in your indexed documents with full pipeline transparency.
      </p>

      {/* Example chips */}
      <div className="flex flex-col gap-2 w-full max-w-sm">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          Try asking
        </p>
        {EXAMPLE_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onQuestion(q)}
            className="flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-left text-xs font-medium text-foreground hover:border-primary/40 hover:bg-accent/60 hover:text-primary transition-all group"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-primary/40 group-hover:bg-primary transition-colors shrink-0" />
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

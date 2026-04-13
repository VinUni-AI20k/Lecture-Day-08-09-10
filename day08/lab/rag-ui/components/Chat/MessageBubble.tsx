"use client";

import React, { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";

// ── ChunkMeta (subset of ChunkRow kept in Message) ───────────────────────────

export interface ChunkMeta {
  chunk_id?: string;
  metadata?: {
    source?: string;
    section?: string;
    [k: string]: unknown;
  };
  document?: string;
  page_content?: string;
  content?: string;
  score?: number;
}

// ── Message type ─────────────────────────────────────────────────────────────

type Role = "user" | "assistant";

export interface Message {
  id: string;
  role: Role;
  text: string;
  isStreaming?: boolean;
  chunks?: ChunkMeta[];
}

// ── Citation chip ─────────────────────────────────────────────────────────────

interface CitationChipProps {
  n: number;
  chunk?: ChunkMeta;
  disabled?: boolean;
}

function CitationChip({ n, chunk, disabled }: CitationChipProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLButtonElement>(null);

  if (disabled || !chunk) {
    return (
      <sup className="inline-flex items-center">
        <span className="citation-chip-static">[{n}]</span>
      </sup>
    );
  }

  const source = chunk.metadata?.source ?? chunk.document ?? "không rõ nguồn";
  const section = chunk.metadata?.section ?? "";
  const preview =
    chunk.page_content ?? chunk.content ?? "";
  const score = chunk.score;

  return (
    <span className="relative inline-flex items-center">
      <button
        ref={ref}
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
        className={cn(
          "citation-chip",
          open && "citation-chip-active"
        )}
      >
        {n}
      </button>

      {open && (
        <>
          {/* Backdrop */}
          <span
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          {/* Card */}
          <span className="citation-card z-50">
            {/* Header */}
            <span className="citation-card-header">
              <span className="flex items-center gap-1.5 min-w-0">
                <FileText className="h-3.5 w-3.5 shrink-0 text-primary" />
                <span className="font-semibold text-foreground truncate text-[11px]">
                  {source}
                </span>
              </span>
              <span className="flex items-center gap-2 shrink-0">
                {score != null && (
                  <span className="text-[10px] font-bold text-primary/80 bg-primary/10 rounded-full px-1.5 py-0.5">
                    {(score * 100).toFixed(0)}%
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            </span>

            {/* Section */}
            {section && (
              <span className="citation-card-section">{section}</span>
            )}

            {/* Preview */}
            {preview && (
              <span className="citation-card-preview">
                {preview.slice(0, 380)}{preview.length > 380 ? "…" : ""}
              </span>
            )}

            {/* Chunk id */}
            {chunk.chunk_id && (
              <span className="citation-card-footer">
                mã đoạn: {chunk.chunk_id}
              </span>
            )}
          </span>
        </>
      )}
    </span>
  );
}

// ── Citation-aware text renderer ──────────────────────────────────────────────

function CitationText({
  text,
  chunks,
  isStreaming,
}: {
  text: string;
  chunks?: ChunkMeta[];
  isStreaming?: boolean;
}) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <>
      {parts.map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/);
        if (m) {
          const n = Number(m[1]);
          const chunk = chunks?.[n - 1];
          return (
            <CitationChip
              key={i}
              n={n}
              chunk={chunk}
              disabled={isStreaming}
            />
          );
        }
        return <React.Fragment key={i}>{part}</React.Fragment>;
      })}
    </>
  );
}

// ── Assistant bubble ──────────────────────────────────────────────────────────

function AssistantBubble({
  text,
  isStreaming,
  chunks,
}: {
  text: string;
  isStreaming?: boolean;
  chunks?: ChunkMeta[];
}) {
  return (
    <div className="group flex flex-col gap-1.5 self-start max-w-[88%] msg-enter">
      <div className="flex items-start gap-2.5">
        {/* AI avatar */}
        <div className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 ring-1 ring-primary/20">
          <span className="text-[10px] font-bold text-primary">AI</span>
        </div>
        {/* Bubble */}
        <div className="rounded-2xl rounded-tl-sm border border-border bg-card px-4 py-3 shadow-sm flex-1 min-w-0">
          <div
            className={cn(
              "prose-answer text-sm text-foreground",
              isStreaming && "streaming-cursor"
            )}
          >
            {isStreaming && !text ? (
              <ThinkingDots />
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Override <p> to inject interactive citations inline
                  p({ children }) {
                    return (
                      <p>
                        {React.Children.map(children, (child) => {
                          if (typeof child === "string") {
                            return (
                              <CitationText
                                text={child}
                                chunks={chunks}
                                isStreaming={isStreaming}
                              />
                            );
                          }
                          return child;
                        })}
                      </p>
                    );
                  },
                  code({ children, className, ...rest }) {
                    const isBlock = className?.includes("language-");
                    return isBlock ? (
                      <code className={cn("block", className)} {...rest}>
                        {children}
                      </code>
                    ) : (
                      <code {...rest}>{children}</code>
                    );
                  },
                }}
              >
                {text}
              </ReactMarkdown>
            )}
          </div>
          {/* Danh sách tài liệu tham chiếu */}
          {!isStreaming && chunks && chunks.length > 0 && (
            <div className="mt-2 pt-2 border-t border-border/60 flex flex-wrap gap-1.5">
              {chunks.slice(0, 8).map((c, i) => {
                const src = c.metadata?.source ?? c.document ?? "doc";
                const name = src.split(/[/\\]/).pop() ?? src;
                return (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 rounded-full border border-primary/20 bg-primary/5 px-2 py-0.5 text-[10px] font-medium text-primary/80"
                  >
                    <span className="font-bold text-primary">[{i + 1}]</span>
                    {name.length > 22 ? name.slice(0, 22) + "…" : name}
                  </span>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Thinking dots ─────────────────────────────────────────────────────────────

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1.5 h-5 py-0.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}

// ── User bubble ───────────────────────────────────────────────────────────────

function UserBubble({ text }: { text: string }) {
  return (
    <div className="self-end max-w-[80%] msg-enter">
      <div
        className="rounded-2xl rounded-tr-sm px-4 py-2.5 shadow-sm"
        style={{ background: "var(--gradient-primary)" }}
      >
        <p className="text-sm font-medium text-white whitespace-pre-wrap leading-relaxed">
          {text}
        </p>
      </div>
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export function MessageBubble({ message }: { message: Message }) {
  return message.role === "user" ? (
    <UserBubble text={message.text} />
  ) : (
    <AssistantBubble
      text={message.text}
      isStreaming={message.isStreaming}
      chunks={message.chunks}
    />
  );
}

// ── Legacy exports kept for backwards compat ─────────────────────────────────
export function CitationChipLegacy({ n }: { n: number }) {
  return <sup className="citation-chip-static">[{n}]</sup>;
}
export function parseCitations(text: string): React.ReactNode[] {
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const m = part.match(/^\[(\d+)\]$/);
    if (m) return <CitationChipLegacy key={i} n={Number(m[1])} />;
    return part;
  });
}

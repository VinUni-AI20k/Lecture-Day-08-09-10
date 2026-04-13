"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

export function CitationChip({ n }: { n: number }) {
  return <sup className="citation-chip">{n}</sup>;
}

export function parseCitations(text: string): React.ReactNode[] {
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const m = part.match(/^\[(\d+)\]$/);
    if (m) return <CitationChip key={i} n={Number(m[1])} />;
    return part;
  });
}

type Role = "user" | "assistant";

export interface Message {
  id: string;
  role: Role;
  text: string;
  isStreaming?: boolean;
}

function AssistantBubble({ text, isStreaming }: { text: string; isStreaming?: boolean }) {
  return (
    <div className="group flex flex-col gap-1.5 self-start max-w-[88%] msg-enter">
      {/* Avatar dot */}
      <div className="flex items-start gap-2.5">
        <div className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 ring-1 ring-primary/20">
          <span className="text-[10px] font-bold text-primary">AI</span>
        </div>
        <div
          className={cn(
            "rounded-2xl rounded-tl-sm border border-border bg-card px-4 py-3 shadow-sm",
            "flex-1 min-w-0"
          )}
        >
          <div className={cn("prose-answer text-sm text-foreground", isStreaming && "streaming-cursor")}>
            {isStreaming && !text ? (
              <ThinkingDots />
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ children, className, ...rest }) {
                    const isBlock = className?.includes("language-");
                    return isBlock ? (
                      <code className={cn("block", className)} {...rest}>{children}</code>
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
        </div>
      </div>
    </div>
  );
}

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

export function MessageBubble({ message }: { message: Message }) {
  return message.role === "user" ? (
    <UserBubble text={message.text} />
  ) : (
    <AssistantBubble text={message.text} isStreaming={message.isStreaming} />
  );
}

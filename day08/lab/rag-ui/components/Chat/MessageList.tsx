"use client";

import * as React from "react";
import { MessageBubble, type Message } from "./MessageBubble";
import { cn } from "@/lib/utils";

interface Props {
  messages: Message[];
  loading: boolean;
  className?: string;
}

export function MessageList({ messages, loading, className }: Props) {
  const bottomRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  if (messages.length === 0 && !loading) {
    return null; // empty state handled by parent
  }

  return (
    <div className={cn("flex flex-col gap-5 px-4 py-6", className)}>
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
      {/* Thinking indicator when loading but no streaming message yet */}
      {loading && !messages.some((m) => m.role === "assistant" && m.isStreaming) && (
        <div className="self-start max-w-[88%] msg-enter">
          <div className="flex items-start gap-2.5">
            <div className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 ring-1 ring-primary/20">
              <span className="text-[10px] font-bold text-primary">AI</span>
            </div>
            <div className="rounded-2xl rounded-tl-sm border border-border bg-card px-4 py-3 shadow-sm">
              <ThinkingIndicator />
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2.5 h-5">
      <div className="thinking-ring h-2 w-2 rounded-full bg-primary" />
      <span className="text-xs text-muted-foreground font-medium tracking-wide">Thinking…</span>
    </div>
  );
}

"use client"

import * as React from "react"

import type { UiMessage } from "@/lib/types/chat-ui"
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { MessageBubble } from "@/components/chat/message-bubble"

const SUGGESTIONS = [
  "SLA ticket P1 xử lý trong bao lâu?",
  "Khi nào cần escalation lên duty manager?",
  "Wi‑Fi văn phòng chậm — checklist IT Helpdesk?",
]

export function ChatMessages({
  messages,
  streamingText,
  loading,
  busy,
  onSuggestionClick,
  className,
}: {
  messages: UiMessage[]
  streamingText: string
  loading: boolean
  /** Đang chờ / stream phản hồi — dùng cho aria-busy trên vùng log. */
  busy?: boolean
  onSuggestionClick: (text: string) => void
  className?: string
}) {
  const bottomRef = React.useRef<HTMLDivElement>(null)
  const reduceMotion = usePrefersReducedMotion()

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: reduceMotion ? "auto" : "smooth",
      block: "end",
    })
  }, [messages, streamingText, loading, reduceMotion])

  const empty = messages.length === 0 && !loading && !streamingText

  return (
    <ScrollArea
      className={cn("h-full min-h-0 flex-1", className)}
      aria-label="Luồng hội thoại"
    >
      <div
        className="flex flex-col gap-4 p-4 pb-2"
        role="log"
        aria-live="polite"
        aria-relevant="additions text"
        aria-busy={busy ?? loading}
      >
        {empty && (
          <div className="mx-auto flex max-w-lg flex-col gap-3 text-center">
            <p className="text-muted-foreground text-sm">
              Demo trợ lý nội bộ CS + IT Helpdesk — luồng RAG, đa agent và
              tín hiệu pipeline (mock SSE).
            </p>
            <div className="flex flex-col gap-2">
              <p className="text-muted-foreground text-xs font-medium">
                Gợi ý câu hỏi
              </p>
              <ul className="flex flex-col gap-2">
                {SUGGESTIONS.map((s) => (
                  <li key={s}>
                    <button
                      type="button"
                      className="bg-secondary/80 hover:bg-secondary text-secondary-foreground w-full rounded-md border border-transparent px-3 py-2 text-left text-sm transition-colors"
                      onClick={() => onSuggestionClick(s)}
                    >
                      {s}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble key={m.id} role={m.role}>
            {m.content}
          </MessageBubble>
        ))}

        {loading && !streamingText && (
          <div className="flex gap-3">
            <Skeleton className="size-8 shrink-0 rounded-full" />
            <div className="flex flex-1 flex-col gap-2">
              <Skeleton className="h-4 w-3/4 max-w-md" />
              <Skeleton className="h-4 w-1/2 max-w-sm" />
            </div>
          </div>
        )}

        {streamingText ? (
          <MessageBubble role="assistant">{streamingText}</MessageBubble>
        ) : null}

        <div ref={bottomRef} className="h-px w-full shrink-0" />
      </div>
    </ScrollArea>
  )
}

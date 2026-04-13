"use client"

import * as React from "react"
import {
  Headset,
  Mail,
  ShieldAlert,
  Wifi,
  type LucideIcon,
} from "lucide-react"

import type { ConfidenceLevel } from "@/lib/types/agent-events"
import type { UiMessage } from "@/lib/types/chat-ui"
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { MessageBubble } from "@/components/chat/message-bubble"
import { MessageSourcesInline } from "@/components/chat/message-sources-inline"
import {
  EmailDraftApprovalCard,
  EmailDraftOutcome,
} from "@/components/chat/email-draft-approval"

type SuggestionItem = {
  prompt: string
  title: string
  subtitle: string
  icon: LucideIcon
}

/** Bốn gợi ý: CS (policy → leo thang → email HIL), sau đó IT. */
const SUGGESTIONS: SuggestionItem[] = [
  {
    prompt: "SLA ticket P1 xử lý trong bao lâu?",
    title: "SLA & ticket P1",
    subtitle: "Policy nội bộ (RAG)",
    icon: ShieldAlert,
  },
  {
    prompt: "Khi nào cần escalation lên duty manager?",
    title: "Escalation",
    subtitle: "Leo thang & runbook",
    icon: Headset,
  },
  {
    prompt:
      "Soạn email chăm sóc khách hàng sau phản hồi chậm — cần xác nhận gửi",
    title: "Email chăm sóc KH",
    subtitle: "Bản nháp, xác nhận gửi (HIL)",
    icon: Mail,
  },
  {
    prompt: "Wi‑Fi văn phòng chậm — checklist IT Helpdesk?",
    title: "IT Helpdesk",
    subtitle: "Wi‑Fi / VPN",
    icon: Wifi,
  },
]

function assistantBubbleVariant(
  level: ConfidenceLevel | null | undefined
): "default" | "lowConfidence" {
  return level === "low" ? "lowConfidence" : "default"
}

export function ChatMessages({
  messages,
  streamingText,
  streamConfidence,
  loading,
  busy,
  onSuggestionClick,
  onConfirmEmailDraft,
  onDismissEmailDraft,
  className,
}: {
  messages: UiMessage[]
  streamingText: string
  /** Độ tin cậy cho bubble đang stream (từ SSE). */
  streamConfidence?: ConfidenceLevel | null
  loading: boolean
  /** Đang chờ / stream phản hồi — dùng cho aria-busy trên vùng log. */
  busy?: boolean
  onSuggestionClick: (text: string) => void
  onConfirmEmailDraft?: (messageId: string) => void
  onDismissEmailDraft?: (messageId: string) => void
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
          <div className="mx-auto flex w-full max-w-2xl flex-col gap-5">
            <div className="text-center">
              <p className="text-foreground text-sm font-medium tracking-tight">
                Chọn một gợi ý để bắt đầu
              </p>
              <p className="text-muted-foreground mt-1 text-xs leading-relaxed">
                Demo trợ lý CS + IT — RAG, pipeline và use case xác nhận email
                (mock SSE).
              </p>
            </div>

            <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => {
                const Icon = s.icon
                return (
                  <li key={s.prompt}>
                    <button
                      type="button"
                      onClick={() => onSuggestionClick(s.prompt)}
                      className={cn(
                        "group border-border bg-card/60 hover:border-primary/30 hover:bg-accent/40 focus-visible:ring-ring flex w-full cursor-pointer gap-3 rounded-xl border p-3 text-left shadow-xs transition-colors",
                        "focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
                      )}
                    >
                      <span className="bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary flex size-10 shrink-0 items-center justify-center rounded-lg transition-colors">
                        <Icon className="size-5" aria-hidden />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="text-foreground block text-sm font-medium leading-snug">
                          {s.title}
                        </span>
                        <span className="text-muted-foreground mt-0.5 block text-xs leading-snug">
                          {s.subtitle}
                        </span>
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>
        )}

        {messages.map((m) =>
          m.role === "user" ? (
            <MessageBubble key={m.id} role="user">
              {m.content}
            </MessageBubble>
          ) : (
            <div key={m.id} className="flex flex-col gap-2">
              <MessageBubble
                role="assistant"
                variant={assistantBubbleVariant(m.confidenceLevel)}
              >
                {m.content}
              </MessageBubble>
              {m.emailDraft?.sendStatus === "pending" &&
              onConfirmEmailDraft &&
              onDismissEmailDraft ? (
                <EmailDraftApprovalCard
                  draft={m.emailDraft}
                  messageId={m.id}
                  onConfirm={onConfirmEmailDraft}
                  onDismiss={onDismissEmailDraft}
                />
              ) : null}
              {m.emailDraft &&
              m.emailDraft.sendStatus !== "pending" ? (
                <EmailDraftOutcome status={m.emailDraft.sendStatus} />
              ) : null}
              <MessageSourcesInline message={m} />
            </div>
          )
        )}

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
          <MessageBubble
            role="assistant"
            variant={assistantBubbleVariant(streamConfidence)}
          >
            {streamingText}
          </MessageBubble>
        ) : null}

        <div ref={bottomRef} className="h-px w-full shrink-0" />
      </div>
    </ScrollArea>
  )
}

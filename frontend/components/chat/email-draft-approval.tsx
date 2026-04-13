"use client"

import { Mail, Send, X } from "lucide-react"

import type { EmailDraftSnapshot } from "@/lib/types/chat-ui"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function EmailDraftApprovalCard({
  draft,
  messageId,
  onConfirm,
  onDismiss,
  className,
}: {
  draft: EmailDraftSnapshot
  messageId: string
  onConfirm: (messageId: string) => void
  onDismiss: (messageId: string) => void
  className?: string
}) {
  if (draft.sendStatus !== "pending") return null

  return (
    <Card
      className={cn(
        "border-primary/25 bg-card/80 max-w-[min(100%,52rem)] shadow-md ring-1 ring-primary/10",
        className
      )}
    >
      <CardHeader className="gap-1 pb-2">
        <div className="flex items-center gap-2">
          <div className="bg-primary/10 text-primary flex size-9 shrink-0 items-center justify-center rounded-lg">
            <Mail className="size-4" aria-hidden />
          </div>
          <div className="min-w-0">
            <CardTitle className="text-sm font-semibold leading-tight">
              Bản nháp email — cần xác nhận gửi
            </CardTitle>
            <p className="text-muted-foreground text-[11px] leading-snug">
              Demo HIL: chỉ khi bạn xác nhận, luồng gửi mới tiếp tục (không gửi
              email thật).
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        <div className="space-y-1.5 text-xs">
          <div className="flex flex-wrap gap-1">
            <span className="text-muted-foreground shrink-0 font-medium">
              Đến:
            </span>
            <span className="font-mono wrap-break-word">{draft.to}</span>
          </div>
          <div className="flex flex-wrap gap-1">
            <span className="text-muted-foreground shrink-0 font-medium">
              Tiêu đề:
            </span>
            <span className="wrap-break-word font-medium">{draft.subject}</span>
          </div>
        </div>
        <div className="border-border bg-muted/30 rounded-lg border p-3">
          <p className="text-muted-foreground mb-1 text-[10px] font-medium uppercase tracking-wide">
            Nội dung
          </p>
          <pre className="text-foreground max-h-48 overflow-y-auto whitespace-pre-wrap wrap-break-word font-sans text-xs leading-relaxed">
            {draft.body}
          </pre>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            className="gap-1.5"
            onClick={() => onConfirm(messageId)}
          >
            <Send className="size-3.5" aria-hidden />
            Xác nhận gửi
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => onDismiss(messageId)}
          >
            <X className="size-3.5" aria-hidden />
            Huỷ
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function EmailDraftOutcome({
  status,
  className,
}: {
  status: Exclude<EmailDraftSnapshot["sendStatus"], "pending">
  className?: string
}) {
  return (
    <p
      className={cn(
        "text-muted-foreground max-w-[min(100%,52rem)] text-[11px] leading-snug",
        className
      )}
    >
      {status === "sent"
        ? "· Email: đã xác nhận gửi (demo — không gửi thật)."
        : "· Email: đã huỷ gửi."}
    </p>
  )
}

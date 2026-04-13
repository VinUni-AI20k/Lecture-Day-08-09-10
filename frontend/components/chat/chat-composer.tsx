"use client"

import * as React from "react"
import { SendHorizontal, Square } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

export function ChatComposer({
  onSend,
  onStop,
  loading,
  className,
}: {
  onSend: (text: string) => void
  onStop: () => void
  loading: boolean
  className?: string
}) {
  const [value, setValue] = React.useState("")
  const hintId = React.useId()

  const submit = () => {
    const t = value.trim()
    if (!t || loading) return
    setValue("")
    onSend(t)
  }

  return (
    <div
      className={cn(
        "border-border bg-background/95 supports-backdrop-filter:backdrop-blur-sm shrink-0 border-t p-3",
        className
      )}
    >
      <div className="mx-auto flex max-w-3xl flex-col gap-2">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Hỏi về SLA, ticket, hoặc IT Helpdesk…"
          rows={2}
          className="min-h-[72px] resize-none"
          disabled={loading}
          onKeyDown={(e) => {
            if (e.key !== "Enter" || e.shiftKey) return
            e.preventDefault()
            submit()
          }}
          aria-label="Nội dung tin nhắn"
          aria-describedby={hintId}
        />
        <p id={hintId} className="text-muted-foreground text-[11px] leading-snug">
          <span className="sr-only">Phím tắt. </span>
          Enter gửi · Shift+Enter xuống dòng
        </p>
        <div className="flex justify-end gap-2">
          {loading ? (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onStop}
              className="gap-1.5"
            >
              <Square className="size-3.5" aria-hidden />
              Dừng
            </Button>
          ) : null}
          <Button
            type="button"
            size="sm"
            onClick={submit}
            disabled={loading || !value.trim()}
            className="gap-1.5"
          >
            <SendHorizontal className="size-3.5" aria-hidden />
            Gửi
          </Button>
        </div>
      </div>
    </div>
  )
}

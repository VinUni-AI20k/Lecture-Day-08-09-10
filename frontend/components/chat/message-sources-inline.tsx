"use client"

import * as React from "react"

import type { RetrievalChunk } from "@/lib/types/agent-events"
import type { UiMessage } from "@/lib/types/chat-ui"
import { SourceCard } from "@/components/sources/source-card"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"

function shortTitle(title: string, max = 28) {
  const t = title.trim()
  if (t.length <= max) return t
  return `${t.slice(0, max - 1)}…`
}

export function MessageSourcesInline({ message }: { message: UiMessage }) {
  const [open, setOpen] = React.useState(false)
  const [selected, setSelected] = React.useState<RetrievalChunk | null>(null)

  if (message.role !== "assistant") return null
  const chunks = message.sourcesUsed
  if (!chunks?.length) return null

  return (
    <>
      <div
        className={cn(
          "border-border bg-muted/25 max-w-[min(100%,52rem)] rounded-lg border px-2 py-1.5"
        )}
      >
        <div className="flex flex-wrap items-center gap-1.5 gap-y-1">
          <span className="text-muted-foreground shrink-0 text-[10px] font-medium tracking-tight sm:text-xs">
            Nguồn đã dùng
          </span>
          {message.routeKey ? (
            <span className="text-muted-foreground font-mono text-[10px] sm:text-[11px]">
              · {message.routeKey}
            </span>
          ) : null}
        </div>
        <div className="mt-1 flex flex-wrap gap-1">
          {chunks.map((c) => (
            <Button
              key={c.id}
              type="button"
              variant="outline"
              size="sm"
              className="h-7 max-w-[min(100%,14rem)] shrink truncate px-2 text-[11px] font-normal"
              onClick={() => {
                setSelected(c)
                setOpen(true)
              }}
            >
              <span className="truncate">{shortTitle(c.title)}</span>
              <span className="text-muted-foreground ml-1 shrink-0 tabular-nums">
                {(c.score * 100).toFixed(0)}%
              </span>
            </Button>
          ))}
        </div>
      </div>

      <Dialog
        open={open}
        onOpenChange={(o) => {
          setOpen(o)
          if (!o) setSelected(null)
        }}
      >
        <DialogContent className="max-h-[min(90vh,36rem)] gap-4 overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-left text-base leading-snug">
              {selected?.title ?? "Nguồn"}
            </DialogTitle>
          </DialogHeader>
          {selected ? (
            <SourceCard chunk={selected} showRetrievalHint={false} />
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  )
}

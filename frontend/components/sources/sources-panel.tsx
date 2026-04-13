"use client"

import type { RetrievalChunk } from "@/lib/types/agent-events"
import { cn } from "@/lib/utils"
import { SourceCard } from "@/components/sources/source-card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"

export function SourcesPanel({
  chunks,
  grounded,
  className,
}: {
  chunks: RetrievalChunk[]
  grounded: boolean | null
  className?: string
}) {
  return (
    <section className={cn("flex flex-col gap-2", className)} aria-label="Nguồn trích dẫn">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold tracking-tight">Nguồn (RAG)</h2>
        {grounded !== null ? (
          <Badge variant={grounded ? "default" : "destructive"}>
            {grounded ? "Có grounding" : "Không khớp tài liệu"}
          </Badge>
        ) : (
          <span className="text-muted-foreground text-xs">Chờ retrieval…</span>
        )}
      </div>
      <Separator />
      {chunks.length === 0 ? (
        <p className="text-muted-foreground py-2 text-xs">
          Chưa có chunk — gửi câu hỏi để demo retrieval.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {chunks.map((c) => (
            <li key={c.id}>
              <SourceCard chunk={c} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

"use client"

import type { RetrievalChunk } from "@/lib/types/agent-events"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

export function SourceCard({
  chunk,
  className,
  showRetrievalHint,
}: {
  chunk: RetrievalChunk
  className?: string
  /** Hiển thị dòng giải thích điểm khớp (dùng dưới bubble assistant). */
  showRetrievalHint?: boolean
}) {
  return (
    <Card className={cn("text-sm shadow-none", className)}>
      <CardHeader className="gap-1 pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-sm leading-snug font-medium">
            {chunk.title}
          </CardTitle>
          <Badge variant="secondary" className="shrink-0 tabular-nums">
            {(chunk.score * 100).toFixed(0)}%
          </Badge>
        </div>
        {showRetrievalHint ? (
          <p className="text-muted-foreground text-[11px] leading-snug">
            % góc phải = độ khớp sau hybrid + rerank (demo).
          </p>
        ) : null}
        {chunk.source ? (
          <p className="text-muted-foreground font-mono text-xs">{chunk.source}</p>
        ) : null}
      </CardHeader>
      <CardContent className="text-muted-foreground pt-0 text-xs leading-relaxed">
        {chunk.excerpt}
      </CardContent>
    </Card>
  )
}

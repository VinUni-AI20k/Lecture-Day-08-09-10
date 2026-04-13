"use client"

import * as React from "react"
import { ClipboardCopy, Route } from "lucide-react"

import type { TraceRow } from "@/lib/types/chat-ui"
import type { AgentNode } from "@/lib/types/agent-events"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Separator } from "@/components/ui/separator"

const NODE_LABEL: Record<AgentNode, string> = {
  supervisor: "Supervisor",
  retrieval: "Retrieval",
  policy: "Policy",
  synthesis: "Synthesis",
}

function NodeBadge({ node }: { node: AgentNode }) {
  return (
    <Badge variant="outline" className="font-mono text-[10px] uppercase">
      {NODE_LABEL[node]}
    </Badge>
  )
}

export function AgentTimeline({
  rows,
  traceId,
  onCopyJson,
  className,
}: {
  rows: TraceRow[]
  traceId?: string
  onCopyJson: () => void
  className?: string
}) {
  return (
    <section
      className={cn("flex flex-col gap-2", className)}
      aria-label="Luồng agent và route"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold tracking-tight">Trace đa agent</h2>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-8 gap-1 text-xs"
          onClick={onCopyJson}
          disabled={rows.length === 0 && !traceId}
        >
          <ClipboardCopy className="size-3.5" aria-hidden />
          Copy JSON
        </Button>
      </div>
      {traceId ? (
        <p className="text-muted-foreground font-mono text-[10px] break-all">
          {traceId}
        </p>
      ) : null}
      <Separator />
      {rows.length === 0 ? (
        <p className="text-muted-foreground py-2 text-xs">
          Chưa có bước — trace xuất hiện khi có luồng supervisor / workers.
        </p>
      ) : (
        <ol className="relative flex flex-col gap-0 border-l border-border pl-4">
          {rows.map((row, i) => (
            <li
              key={`${row.kind}-${i}`}
              className="relative pb-3 pl-0 last:pb-0"
            >
              <div
                className="bg-border absolute top-1.5 left-0 size-2 -translate-x-[calc(50%+0.5px)] rounded-full"
                aria-hidden
              />
              {row.kind === "step" ? (
                <Collapsible defaultOpen>
                  <CollapsibleTrigger className="flex w-full items-center justify-between gap-2 text-left text-sm font-medium hover:underline">
                    <span>{row.label}</span>
                    <NodeBadge node={row.node} />
                  </CollapsibleTrigger>
                  <CollapsibleContent className="text-muted-foreground pt-1 text-xs">
                    Bước <code className="font-mono">{row.stepId}</code> — node{" "}
                    <code className="font-mono">{row.node}</code>
                  </CollapsibleContent>
                </Collapsible>
              ) : (
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Route className="text-muted-foreground size-4 shrink-0" />
                    Route: <span className="font-mono">{row.route}</span>
                  </div>
                  <p className="text-muted-foreground pl-6 text-xs leading-relaxed">
                    {row.reason}
                  </p>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

"use client"

import * as React from "react"
import Link from "next/link"
import { Gauge, MessageSquarePlus, PanelRight } from "lucide-react"

import { useAgentChat } from "@/hooks/use-agent-chat"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { ChatMessages } from "@/components/chat/chat-messages"
import { ChatComposer } from "@/components/chat/chat-composer"
import { PipelineMetricsStrip } from "@/components/pipeline/pipeline-metrics-strip"
import { SourcesPanel } from "@/components/sources/sources-panel"
import { AgentTimeline } from "@/components/agent-trace/agent-timeline"

function InsightColumn({
  className,
  traceRows,
  sources,
  pipeline,
  grounded,
  lastTraceId,
  copyTraceJson,
}: {
  className?: string
} & Pick<
  ReturnType<typeof useAgentChat>,
  | "traceRows"
  | "sources"
  | "pipeline"
  | "grounded"
  | "lastTraceId"
  | "copyTraceJson"
>) {
  return (
    <ScrollArea className={cn("min-h-0 flex-1", className)}>
      <div className="flex flex-col gap-6 p-4">
        <PipelineMetricsStrip metrics={pipeline} />
        <Separator />
        <SourcesPanel chunks={sources} grounded={grounded} />
        <Separator />
        <AgentTimeline
          rows={traceRows}
          traceId={lastTraceId}
          onCopyJson={copyTraceJson}
        />
      </div>
    </ScrollArea>
  )
}

export function AssistantWorkspace() {
  const chat = useAgentChat()
  const [mobileOpen, setMobileOpen] = React.useState(false)

  const insightProps = {
    traceRows: chat.traceRows,
    sources: chat.sources,
    pipeline: chat.pipeline,
    grounded: chat.grounded,
    lastTraceId: chat.lastTraceId,
    copyTraceJson: chat.copyTraceJson,
  }

  return (
    <div className="bg-background flex min-h-0 flex-1 flex-col overflow-hidden">
      <header className="border-border flex shrink-0 items-center justify-between gap-3 border-b px-3 py-2.5 sm:px-4">
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold tracking-tight">
            Trợ lý nội bộ
          </h1>
          <p className="text-muted-foreground truncate text-xs">
            RAG · Supervisor / workers · Pipeline (mock SSE)
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => chat.clearSession()}
            disabled={chat.messages.length === 0 && !chat.loading}
            aria-label="Xoá và bắt đầu cuộc trò chuyện mới"
          >
            <MessageSquarePlus className="size-4" aria-hidden />
            <span className="hidden sm:inline">Cuộc mới</span>
          </Button>
          <Button variant="ghost" size="sm" className="hidden sm:inline-flex" asChild>
            <Link href="/pipeline" className="gap-1.5">
              <Gauge className="size-4" aria-hidden />
              Pipeline
            </Link>
          </Button>
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="md:hidden"
                aria-label="Mở panel trace và nguồn"
              >
                <PanelRight className="size-4" />
                Trace
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="flex w-full flex-col p-0 sm:max-w-md">
              <SheetHeader className="border-border shrink-0 border-b p-4 text-left">
                <SheetTitle>Trace & nguồn</SheetTitle>
              </SheetHeader>
              <InsightColumn className="flex-1" {...insightProps} />
            </SheetContent>
          </Sheet>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden md:flex-row">
        <section
          className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden"
          aria-labelledby="assistant-chat-heading"
        >
          <h2 id="assistant-chat-heading" className="sr-only">
            Khung hội thoại
          </h2>
          <ChatMessages
            messages={chat.messages}
            streamingText={chat.streamingText}
            loading={chat.loading}
            onSuggestionClick={(t) => {
              void chat.send(t)
            }}
            busy={chat.loading}
            className="min-h-0 flex-1"
          />
          <ChatComposer
            onSend={(t) => {
              void chat.send(t)
            }}
            onStop={chat.stop}
            loading={chat.loading}
            className="shrink-0"
          />
        </section>

        <aside
          className="border-border bg-card/30 hidden min-h-0 w-full max-w-md shrink-0 flex-col overflow-hidden border-l md:flex"
          aria-label="Trace, nguồn và pipeline"
        >
          <InsightColumn {...insightProps} />
        </aside>
      </div>
    </div>
  )
}

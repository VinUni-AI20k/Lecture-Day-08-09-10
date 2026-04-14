"use client";

import * as React from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { StepTimeline } from "./StepTimeline";
import { TelemetryCard } from "./TelemetryCard";
import { SourcesSection } from "./SourcesSection";
import type { RagResponse } from "@/lib/rag-client";
import { cn } from "@/lib/utils";
import { Brain } from "lucide-react";

interface Props {
  last: RagResponse | null;
  loading: boolean;
  streamingSteps?: RagResponse["pipeline_steps"];
  className?: string;
}

export function InspectorPanel({ last, loading, streamingSteps, className }: Props) {
  // While loading → show live streaming steps as they arrive.
  // After done  → prefer last.pipeline_steps (contains step5 + full data).
  const steps = loading
    ? (streamingSteps ?? [])
    : (last?.pipeline_steps ?? streamingSteps ?? []);

  return (
    <aside className={cn("flex flex-col h-full", className)} style={{ background: "var(--sidebar)" }}>
      {/* Header — matches main gradient header */}
      <div
        className="shrink-0 px-4 py-3.5"
        style={{ background: "var(--gradient-header)" }}
      >
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/20">
            <Brain className="h-3.5 w-3.5 text-white" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white tracking-tight">Trình Kiểm Tra RAG</h2>
            <p className="text-[10px] text-blue-200/80 leading-none mt-0.5">
              Trực quan hóa pipeline theo thời gian thực
            </p>
          </div>
        </div>
      </div>

      {/* Scrollable content */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-3 space-y-3">

          {/* Pipeline Steps — always first */}
          <section>
            <SectionLabel>Các bước xử lý</SectionLabel>
            <StepTimeline
              steps={steps}
              loading={loading}
              totalSteps={5}
            />
          </section>

          {/* Telemetry — shown once done */}
          {last && !loading && (
            <section>
              <SectionLabel>Hiệu Suất</SectionLabel>
              <TelemetryCard
                telemetry={last.telemetry}
                requestId={last.request_id}
                config={last.config}
              />
            </section>
          )}

          {/* Sources */}
          {last && !loading && (last.sources?.length ?? 0) > 0 && (
            <section>
              <SectionLabel>Nguồn Tài Liệu</SectionLabel>
              <SourcesSection sources={last.sources ?? []} />
            </section>
          )}

          {/* Spacer */}
          <div className="h-4" />
        </div>
      </ScrollArea>
    </aside>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-0.5">
      {children}
    </p>
  );
}

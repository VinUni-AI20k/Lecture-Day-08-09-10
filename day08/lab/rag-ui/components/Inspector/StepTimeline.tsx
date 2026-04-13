"use client";

import * as React from "react";
import {
  MessageSquare,
  Database,
  Filter,
  FileText,
  Sparkles,
  ChevronDown,
  Loader2,
} from "lucide-react";
import type { PipelineStep, ScoreStats } from "@/lib/rag-client";
import { ChunkTable } from "./ChunkTable";
import { cn } from "@/lib/utils";

// ── Step metadata ────────────────────────────────────────────────────────────

const STEP_META: Record<
  number,
  {
    label: string;
    description: string;
    icon: React.FC<{ className?: string }>;
    color: string;
  }
> = {
  1: {
    label: "Query Understanding",
    description: "Analyzing your question and choosing retrieval strategy",
    icon: MessageSquare,
    color: "var(--step-1)",
  },
  2: {
    label: "Document Retrieval",
    description: "Searching the vector store for relevant chunks",
    icon: Database,
    color: "var(--step-2)",
  },
  3: {
    label: "Selection & Rerank",
    description: "Filtering the best evidence for the LLM",
    icon: Filter,
    color: "var(--step-3)",
  },
  4: {
    label: "Context Assembly",
    description: "Building the grounded prompt with citations",
    icon: FileText,
    color: "var(--step-4)",
  },
  5: {
    label: "LLM Generation",
    description: "Generating a grounded answer from evidence",
    icon: Sparkles,
    color: "var(--step-5)",
  },
};

// ── Individual step card ─────────────────────────────────────────────────────

function StepCard({
  step,
  isActive,
  isPending,
  index,
}: {
  step: PipelineStep;
  isActive: boolean;
  isPending: boolean;
  index: number;
}) {
  const [open, setOpen] = React.useState(false);
  const meta = STEP_META[step.step] ?? {
    label: step.name,
    description: "",
    icon: FileText,
    color: "var(--primary)",
  };
  const Icon = meta.icon;
  const hasExpand =
    !isPending && (step.detail || step.context_preview || step.prompt_preview || (step.table && step.table.length > 0));

  return (
    <div
      className="step-enter rounded-xl border border-border bg-card overflow-hidden"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      {/* Left accent bar */}
      <div
        className="flex items-stretch"
        style={{ borderLeft: `3px solid ${isPending ? "var(--border)" : meta.color}` }}
      >
        <div className="flex-1 p-3">
          {/* Header row */}
          <button
            type="button"
            onClick={() => hasExpand && setOpen((o) => !o)}
            className={cn(
              "flex w-full items-start gap-3 text-left",
              hasExpand && "cursor-pointer"
            )}
          >
            {/* Icon */}
            <div
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg mt-0.5"
              style={{
                background: isPending ? "var(--muted)" : `${meta.color}18`,
                color: isPending ? "var(--muted-foreground)" : meta.color,
              }}
            >
              {isActive ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Icon className="h-3.5 w-3.5" />
              )}
            </div>

            {/* Text */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span
                  className={cn(
                    "text-xs font-semibold tracking-wide leading-tight",
                    isPending ? "text-muted-foreground" : "text-foreground"
                  )}
                >
                  {step.step}. {meta.label}
                </span>

                {/* Badges */}
                <div className="flex items-center gap-1 shrink-0">
                  {!isPending && step.step === 2 && step.table && (
                    <span
                      className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                      style={{ background: `${meta.color}18`, color: meta.color }}
                    >
                      {step.table.length} chunks
                    </span>
                  )}
                  {!isPending && step.stats?.score && (
                    <ScoreBadge score={step.stats.score} color={meta.color} />
                  )}
                  {!isPending && step.step === 5 && step.answer_chars && (
                    <span
                      className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                      style={{ background: `${meta.color}18`, color: meta.color }}
                    >
                      {step.answer_chars} chars
                    </span>
                  )}
                  {hasExpand && (
                    <ChevronDown
                      className={cn(
                        "h-3.5 w-3.5 text-muted-foreground transition-transform",
                        open && "rotate-180"
                      )}
                    />
                  )}
                </div>
              </div>

              {/* Short detail */}
              {!isPending && step.detail && (
                <p className="mt-1 text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                  {step.detail.replace(/\*\*/g, "")}
                </p>
              )}

              {/* Stats inline summary (QuachGiaDuoc enrichment) */}
              {!isPending && step.stats && (
                <StatsRow stats={step.stats} color={meta.color} />
              )}

              {/* Pending skeleton */}
              {isPending && (
                <div className="mt-1.5 flex flex-col gap-1">
                  <div className="skeleton h-2 w-3/4" />
                  <div className="skeleton h-2 w-1/2" />
                </div>
              )}

              {/* Query badge for step 1 */}
              {!isPending && step.step === 1 && step.query && (
                <div className="mt-2 rounded-lg bg-muted px-2.5 py-1.5 text-[11px] text-foreground font-medium leading-snug border border-border">
                  &ldquo;{step.query}&rdquo;
                </div>
              )}
            </div>
          </button>

          {/* Expanded content */}
          {open && !isPending && (
            <div className="mt-3 space-y-2 pl-10">
              {/* Chunk table for steps 2 and 3 */}
              {(step.step === 2 || step.step === 3) && step.table && step.table.length > 0 && (
                <ChunkTable rows={step.table} maxVisible={3} />
              )}

              {/* Context / prompt preview */}
              {(step.context_preview || step.prompt_preview) && (
                <pre className="max-h-52 overflow-auto rounded-lg bg-muted border border-border px-3 py-2 text-[11px] text-muted-foreground whitespace-pre-wrap leading-relaxed">
                  {step.context_preview ?? step.prompt_preview}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Stats helpers ────────────────────────────────────────────────────────────

function ScoreBadge({ score, color }: { score: ScoreStats; color: string }) {
  const pct = Math.round(score.avg * 100);
  return (
    <span
      className="text-[10px] font-bold px-1.5 py-0.5 rounded-full"
      title={`min=${score.min.toFixed(3)} avg=${score.avg.toFixed(3)} max=${score.max.toFixed(3)}`}
      style={{ background: `${color}18`, color }}
    >
      avg {pct}%
    </span>
  );
}

function StatsRow({
  stats,
  color,
}: {
  stats: NonNullable<PipelineStep["stats"]>;
  color: string;
}) {
  const pills: { label: string; value: string | number }[] = [];
  if (stats.non_empty_chunks != null) pills.push({ label: "non-empty", value: stats.non_empty_chunks });
  if (stats.dropped_candidates != null) pills.push({ label: "dropped", value: stats.dropped_candidates });
  if (stats.sources_preview) pills.push({ label: "sources", value: stats.sources_preview });
  if (pills.length === 0) return null;

  return (
    <div className="mt-1.5 flex flex-wrap gap-1.5">
      {pills.map((p) => (
        <span
          key={p.label}
          className="inline-flex items-center gap-1 text-[10px] rounded-md px-1.5 py-0.5 border"
          style={{ borderColor: `${color}30`, color: "var(--muted-foreground)", background: `${color}08` }}
        >
          <span style={{ color }} className="font-semibold">{p.label}</span>
          {p.value}
        </span>
      ))}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

interface Props {
  steps: PipelineStep[];
  loading?: boolean;
  totalSteps?: number;
}

export function StepTimeline({ steps, loading, totalSteps = 5 }: Props) {
  const completedNums = new Set(steps.map((s) => s.step));
  const lastCompleted = steps.length > 0 ? Math.max(...steps.map((s) => s.step)) : 0;
  const activeStep = loading ? lastCompleted + 1 : 0;

  if (!loading && !steps.length) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-10 text-center px-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/8 ring-2 ring-primary/12">
          <Database className="h-5 w-5 text-primary/60" />
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground">RAG Pipeline</p>
          <p className="mt-1 text-xs text-muted-foreground leading-relaxed max-w-[200px]">
            Send a question to watch the 5-step pipeline run in real time.
          </p>
        </div>
      </div>
    );
  }

  // Build list: completed steps + pending placeholders
  const allSteps: { step: PipelineStep | null; num: number }[] = [];
  for (let i = 1; i <= totalSteps; i++) {
    const found = steps.find((s) => s.step === i);
    allSteps.push({ step: found ?? null, num: i });
  }

  return (
    <div className="flex flex-col gap-2">
      {allSteps.map(({ step, num }, idx) => {
        const isPending = !completedNums.has(num);
        const isActive = num === activeStep && !!loading;

        if (isPending && !loading) return null;

        const displayStep: PipelineStep = step ?? {
          step: num,
          name: STEP_META[num]?.label ?? `Step ${num}`,
          emoji: "",
        };

        return (
          <StepCard
            key={num}
            step={displayStep}
            isActive={isActive}
            isPending={isPending}
            index={idx}
          />
        );
      })}
    </div>
  );
}

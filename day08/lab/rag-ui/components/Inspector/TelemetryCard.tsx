"use client";

import type { RagTelemetry, RagResponse } from "@/lib/rag-client";
import { Clock, Cpu, DollarSign, Zap } from "lucide-react";

interface TelemetryProps {
  telemetry: RagTelemetry;
  requestId: string;
  config: RagResponse["config"];
}

export function TelemetryCard({ telemetry, requestId, config }: TelemetryProps) {
  const totalUsd = telemetry.cost_usd?.total_usd ?? 0;
  const durationMs = telemetry.duration_ms ?? 0;
  const promptTokens = telemetry.usage?.chat?.prompt_tokens ?? 0;
  const completionTokens = telemetry.usage?.chat?.completion_tokens ?? 0;
  const totalTokens = promptTokens + completionTokens;
  const mode = String(config.retrieval_mode ?? "dense");
  const rerank = config.use_rerank ? "Bật" : "Tắt";

  // Duration bar — cap at 15 000ms for visual
  const durationPct = Math.min((durationMs / 15000) * 100, 100);

  // Token donut — prompt vs completion
  const totalForDonut = Math.max(totalTokens, 1);
  const completionPct = Math.round((completionTokens / totalForDonut) * 100);

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Số Liệu Kỹ Thuật
        </p>
        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-mono font-semibold text-primary">
          {telemetry.run_id?.slice(0, 8) ?? "—"}
        </span>
      </div>

      {/* Duration */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>Thời gian xử lý</span>
          </div>
          <span className="font-mono text-xs font-semibold text-foreground">
            {durationMs >= 1000 ? `${(durationMs / 1000).toFixed(2)}s` : `${durationMs}ms`}
          </span>
        </div>
        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${durationPct}%`,
              background: "var(--gradient-primary)",
            }}
          />
        </div>
      </div>

      {/* Cost + Tokens row */}
      <div className="grid grid-cols-2 gap-3">
        {/* Cost */}
        <div className="rounded-lg bg-muted/50 px-3 py-2.5 space-y-0.5">
          <div className="flex items-center gap-1 text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
            <DollarSign className="h-2.5 w-2.5" />
            Chi phí
          </div>
          <p className="text-base font-bold text-foreground tabular-nums">
            ${totalUsd.toFixed(4)}
          </p>
          <p className="text-[10px] text-muted-foreground">ước tính</p>
        </div>

        {/* Token donut */}
        <div className="rounded-lg bg-muted/50 px-3 py-2.5 space-y-0.5">
          <div className="flex items-center gap-1 text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
            <Zap className="h-2.5 w-2.5" />
            Token sử dụng
          </div>
          <div className="flex items-center gap-2">
            {/* Mini donut */}
            <div
              className="h-8 w-8 rounded-full shrink-0"
              style={{
                background: `conic-gradient(var(--primary) ${completionPct * 3.6}deg, var(--muted) 0deg)`,
              }}
            >
              <div className="h-full w-full rounded-full bg-muted/50 scale-[0.6]" />
            </div>
            <div>
              <p className="text-sm font-bold text-foreground tabular-nums">{totalTokens}</p>
              <p className="text-[10px] text-muted-foreground leading-tight">
                {promptTokens}p + {completionTokens}c
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Config */}
      <div className="flex flex-wrap gap-1.5">
        <ConfigChip icon={<Cpu className="h-2.5 w-2.5" />} label={mode} />
        <ConfigChip icon={<span className="text-[9px] font-bold">K</span>} label={`${config.top_k_search ?? "—"}→${config.top_k_select ?? "—"}`} />
        <ConfigChip icon={<Zap className="h-2.5 w-2.5" />} label={`Sắp xếp lại: ${rerank}`} />
      </div>

      {/* Request ID */}
      <div className="pt-1 border-t border-border">
        <p className="text-[9px] text-muted-foreground uppercase tracking-widest mb-1">Mã yêu cầu</p>
        <code className="break-all text-[10px] font-mono text-muted-foreground leading-relaxed">
          {requestId}
        </code>
      </div>
    </div>
  );
}

function ConfigChip({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-1 rounded-full bg-accent px-2 py-0.5 text-[10px] font-semibold text-accent-foreground">
      {icon}
      {label}
    </div>
  );
}

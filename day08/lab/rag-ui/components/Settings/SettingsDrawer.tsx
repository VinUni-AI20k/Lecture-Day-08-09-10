"use client";

import * as React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { getRagApiBase } from "@/lib/rag-client";
import { cn } from "@/lib/utils";
import {
  Zap,
  BookOpen,
  GitMerge,
  Layers,
  Gauge,
  Sparkles,
  CheckCircle2,
} from "lucide-react";

export interface Settings {
  mode: "dense" | "sparse" | "hybrid";
  useRerank: boolean;
  topKSearch: number;
  topKSelect: number;
}

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  settings: Settings;
  onChange: (s: Settings) => void;
}

// ── Mode cards ────────────────────────────────────────────────────────────────
const MODES: {
  value: Settings["mode"];
  label: string;
  icon: React.FC<{ className?: string }>;
  color: string;
  description: string;
  badge: string;
}[] = [
  {
    value: "dense",
    label: "Dense",
    icon: Zap,
    color: "#2563eb",
    description: "Vector similarity search using embeddings. Best for semantic questions.",
    badge: "Recommended",
  },
  {
    value: "sparse",
    label: "Sparse",
    icon: BookOpen,
    color: "#7c3aed",
    description: "Keyword-based BM25 search. Best for exact term matching.",
    badge: "Keyword",
  },
  {
    value: "hybrid",
    label: "Hybrid",
    icon: GitMerge,
    color: "#0891b2",
    description: "Dense + BM25 combined via RRF fusion. Best overall coverage.",
    badge: "Best coverage",
  },
];

// ── Presets ───────────────────────────────────────────────────────────────────
const PRESETS: { label: string; icon: React.FC<{ className?: string }>; settings: Settings }[] = [
  {
    label: "Fast",
    icon: Gauge,
    settings: { mode: "dense", useRerank: false, topKSearch: 8, topKSelect: 3 },
  },
  {
    label: "Balanced",
    icon: Layers,
    settings: { mode: "hybrid", useRerank: false, topKSearch: 12, topKSelect: 4 },
  },
  {
    label: "Thorough",
    icon: Sparkles,
    settings: { mode: "hybrid", useRerank: true, topKSearch: 20, topKSelect: 6 },
  },
];

// ── Component ─────────────────────────────────────────────────────────────────
export function SettingsDrawer({ open, onOpenChange, settings, onChange }: Props) {
  const api = getRagApiBase();

  function patch(partial: Partial<Settings>) {
    onChange({ ...settings, ...partial });
  }

  function applyPreset(preset: Settings) {
    onChange(preset);
  }

  const activeMode = MODES.find((m) => m.value === settings.mode)!;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px] p-0 overflow-hidden gap-0">
        {/* Header with gradient */}
        <div
          className="px-6 py-5"
          style={{ background: "var(--gradient-primary)" }}
        >
          <DialogHeader>
            <DialogTitle className="text-white text-base font-bold tracking-tight">
              Retrieval Settings
            </DialogTitle>
            <p className="text-blue-100/80 text-xs mt-0.5">
              Configure your RAG pipeline parameters
            </p>
          </DialogHeader>
        </div>

        <div className="px-5 py-4 space-y-5 max-h-[75vh] overflow-y-auto">

          {/* ── Presets ─────────────────────────────────────────────── */}
          <section>
            <SectionLabel>Quick Presets</SectionLabel>
            <div className="grid grid-cols-3 gap-2">
              {PRESETS.map((p) => {
                const Icon = p.icon;
                const isActive =
                  p.settings.mode === settings.mode &&
                  p.settings.useRerank === settings.useRerank &&
                  p.settings.topKSearch === settings.topKSearch &&
                  p.settings.topKSelect === settings.topKSelect;
                return (
                  <button
                    key={p.label}
                    type="button"
                    onClick={() => applyPreset(p.settings)}
                    className={cn(
                      "flex flex-col items-center gap-1.5 rounded-xl border px-3 py-3 text-xs font-semibold transition-all",
                      isActive
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-muted/40 text-muted-foreground hover:border-primary/40 hover:bg-accent/60 hover:text-primary"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {p.label}
                    {isActive && <CheckCircle2 className="h-3 w-3 text-primary" />}
                  </button>
                );
              })}
            </div>
          </section>

          {/* ── Retrieval Mode ──────────────────────────────────────── */}
          <section>
            <SectionLabel>Retrieval Mode</SectionLabel>
            <div className="space-y-2">
              {MODES.map((m) => {
                const Icon = m.icon;
                const isActive = settings.mode === m.value;
                return (
                  <button
                    key={m.value}
                    type="button"
                    onClick={() => patch({ mode: m.value })}
                    className={cn(
                      "flex w-full items-start gap-3 rounded-xl border p-3 text-left transition-all",
                      isActive
                        ? "border-2 shadow-sm"
                        : "border-border bg-muted/20 hover:bg-accent/40"
                    )}
                    style={
                      isActive
                        ? { borderColor: m.color, background: `${m.color}0d` }
                        : {}
                    }
                  >
                    <div
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
                      style={{ background: isActive ? `${m.color}18` : "var(--muted)", color: isActive ? m.color : "var(--muted-foreground)" }}
                    >
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className="text-sm font-semibold"
                          style={{ color: isActive ? m.color : "var(--foreground)" }}
                        >
                          {m.label}
                        </span>
                        <span
                          className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
                          style={{
                            background: isActive ? `${m.color}18` : "var(--muted)",
                            color: isActive ? m.color : "var(--muted-foreground)",
                          }}
                        >
                          {m.badge}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-muted-foreground leading-snug">
                        {m.description}
                      </p>
                    </div>
                    {isActive && (
                      <CheckCircle2
                        className="h-4 w-4 shrink-0 mt-0.5"
                        style={{ color: m.color }}
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </section>

          {/* ── top_k_search ───────────────────────────────────────── */}
          <section>
            <SectionLabel>Retrieval Depth</SectionLabel>
            <div className="rounded-xl border border-border bg-muted/30 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    Candidates to fetch
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Wider pool = more recall, slower
                  </p>
                </div>
                <div
                  className="flex h-9 w-9 items-center justify-center rounded-xl text-sm font-bold text-white"
                  style={{ background: "var(--gradient-primary)" }}
                >
                  {settings.topKSearch}
                </div>
              </div>
              <Slider
                min={3}
                max={24}
                step={1}
                value={[settings.topKSearch]}
                onValueChange={([v]) =>
                  patch({
                    topKSearch: v,
                    topKSelect: Math.min(settings.topKSelect, v),
                  })
                }
              />
              <div className="flex justify-between text-[10px] text-muted-foreground font-medium">
                <span>Narrow (3)</span>
                <span>Wide (24)</span>
              </div>
            </div>
          </section>

          {/* ── top_k_select ───────────────────────────────────────── */}
          <section>
            <div className="rounded-xl border border-border bg-muted/30 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    Chunks into prompt
                  </p>
                  <p className="text-xs text-muted-foreground">
                    More chunks = richer context, higher cost
                  </p>
                </div>
                <div
                  className="flex h-9 w-9 items-center justify-center rounded-xl text-sm font-bold"
                  style={{ background: "var(--primary-subtle)", color: "var(--primary-subtle-foreground)" }}
                >
                  {settings.topKSelect}
                </div>
              </div>
              <Slider
                min={1}
                max={settings.topKSearch}
                step={1}
                value={[settings.topKSelect]}
                onValueChange={([v]) => patch({ topKSelect: v })}
              />
              <div className="flex justify-between text-[10px] text-muted-foreground font-medium">
                <span>Focused (1)</span>
                <span>Broad ({settings.topKSearch})</span>
              </div>
            </div>
          </section>

          {/* ── Rerank ─────────────────────────────────────────────── */}
          <section>
            <div
              className={cn(
                "flex items-start gap-3 rounded-xl border p-4 transition-all",
                settings.useRerank
                  ? "border-primary/40 bg-primary/5"
                  : "border-border bg-muted/20"
              )}
            >
              <div
                className={cn(
                  "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
                  settings.useRerank ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground"
                )}
              >
                <Sparkles className="h-4 w-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-foreground">
                  Cross-encoder Rerank
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed">
                  Re-scores each (query, chunk) pair using a cross-encoder model.
                  Slower but significantly more accurate.
                </p>
                {settings.useRerank && (
                  <p className="mt-1 text-xs font-medium text-primary">
                    ✓ Enabled — using cross-encoder/ms-marco-MiniLM-L-6-v2
                  </p>
                )}
              </div>
              <Switch
                id="rerank-switch"
                checked={settings.useRerank}
                onCheckedChange={(v) => patch({ useRerank: v })}
                className="shrink-0"
              />
            </div>
          </section>

          {/* ── Pipeline summary ───────────────────────────────────── */}
          <section>
            <div className="flex flex-wrap gap-2">
              <PipelinePill
                label="Mode"
                value={activeMode.label}
                color={activeMode.color}
              />
              <PipelinePill
                label="Fetch"
                value={`${settings.topKSearch} chunks`}
                color="#059669"
              />
              <PipelinePill
                label="Use"
                value={`${settings.topKSelect} chunks`}
                color="#0891b2"
              />
              <PipelinePill
                label="Rerank"
                value={settings.useRerank ? "ON" : "off"}
                color={settings.useRerank ? "#ea580c" : undefined}
              />
            </div>
          </section>

          {/* ── API info ────────────────────────────────────────────── */}
          <section className="pb-1">
            <div className="flex items-center justify-between rounded-lg bg-muted/50 border border-border px-3 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                FastAPI
              </span>
              <code className="text-[11px] font-mono text-foreground">
                {api || "http://127.0.0.1:8010"}/api/rag
              </code>
            </div>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
      {children}
    </p>
  );
}

function PipelinePill({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="flex items-center gap-1.5 rounded-full border border-border bg-card px-2.5 py-1 text-xs">
      <span className="text-muted-foreground font-medium">{label}:</span>
      <span
        className="font-bold"
        style={{ color: color ?? "var(--foreground)" }}
      >
        {value}
      </span>
    </div>
  );
}

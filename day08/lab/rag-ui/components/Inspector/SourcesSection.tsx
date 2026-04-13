"use client";

import { FileText, ExternalLink } from "lucide-react";

interface Props {
  sources: string[];
}

export function SourcesSection({ sources }: Props) {
  if (!sources.length) return null;

  return (
    <div className="rounded-xl border border-border bg-card p-3 space-y-2">
      <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        Tài liệu tham chiếu ({sources.length})
      </p>
      <ul className="space-y-1.5">
        {sources.map((src, i) => (
          <li key={src}>
            <div className="flex items-start gap-2.5 rounded-lg border border-border bg-muted/30 px-3 py-2 hover:bg-accent/40 hover:border-primary/30 transition-all cursor-default group">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10 mt-0.5">
                <FileText className="h-3 w-3 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-1">
                  <span className="text-xs font-semibold text-foreground leading-snug">
                    <span className="text-primary mr-1">[{i + 1}]</span>
                    {src.split("/").pop() ?? src}
                  </span>
                  <ExternalLink className="h-3 w-3 text-muted-foreground/40 group-hover:text-primary/60 transition-colors shrink-0 mt-0.5" />
                </div>
                {src.includes("/") && (
                  <p className="mt-0.5 text-[10px] text-muted-foreground truncate">{src}</p>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

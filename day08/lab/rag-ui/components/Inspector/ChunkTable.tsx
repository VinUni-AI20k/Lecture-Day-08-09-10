"use client";

import * as React from "react";
import type { ChunkRow } from "@/lib/rag-client";
import { cn } from "@/lib/utils";

interface Props {
  rows: ChunkRow[];
  maxVisible?: number;
}

export function ChunkTable({ rows, maxVisible = 3 }: Props) {
  const [expanded, setExpanded] = React.useState(false);
  if (!rows.length) return null;

  const visible = expanded ? rows : rows.slice(0, maxVisible);
  const hasMore = rows.length > maxVisible;

  return (
    <div className="mt-2 rounded-lg border border-border overflow-hidden">
      <table className="w-full text-[11px]">
        <thead>
          <tr className="bg-muted/60 text-muted-foreground">
            <th className="px-2 py-1.5 text-left font-semibold w-6">#</th>
            <th className="px-2 py-1.5 text-left font-semibold">Source</th>
            <th className="px-2 py-1.5 text-left font-semibold hidden sm:table-cell">Section</th>
            <th className="px-2 py-1.5 text-left font-semibold w-20">Score</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((row) => (
            <tr
              key={row["#"]}
              className="border-t border-border hover:bg-muted/30 transition-colors"
            >
              <td className="px-2 py-1.5 text-muted-foreground font-mono">{row["#"]}</td>
              <td className="px-2 py-1.5 max-w-[120px]">
                <span className="block truncate font-medium text-foreground" title={row.source}>
                  {row.source || "—"}
                </span>
                {row.preview && (
                  <span className="block truncate text-muted-foreground mt-0.5" title={row.preview}>
                    {row.preview}
                  </span>
                )}
              </td>
              <td className="px-2 py-1.5 max-w-[100px] hidden sm:table-cell">
                <span className="truncate block text-muted-foreground" title={row.section}>
                  {row.section || "—"}
                </span>
              </td>
              <td className="px-2 py-1.5">
                <div className="flex items-center gap-1.5">
                  <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                    <div
                      className="score-bar-fill"
                      style={{ width: `${Math.min(Math.max(row.score * 100, 2), 100)}%` }}
                    />
                  </div>
                  <span className={cn("font-mono text-[10px] shrink-0", row.score > 0.5 ? "text-primary" : "text-muted-foreground")}>
                    {row.score.toFixed(3)}
                  </span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {hasMore && (
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="w-full py-1.5 text-[11px] text-muted-foreground hover:text-primary hover:bg-muted/30 transition-colors border-t border-border font-medium"
        >
          {expanded ? "Show less" : `Show all ${rows.length} chunks`}
        </button>
      )}
    </div>
  );
}

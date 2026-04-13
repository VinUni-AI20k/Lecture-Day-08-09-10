"use client"

import * as React from "react"
import { Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"

export function ChatActivityStrip({
  loading,
  label,
  className,
}: {
  loading: boolean
  label: string | null
  className?: string
}) {
  if (!loading && !label) return null

  const text = label ?? (loading ? "Đang xử lý…" : "")

  return (
    <div
      className={cn(
        "border-border bg-muted/40 text-muted-foreground flex min-h-9 shrink-0 items-center gap-2 border-b px-3 py-1.5 text-xs sm:px-4",
        className
      )}
      role="status"
      aria-live="polite"
      aria-busy={loading}
    >
      {loading ? (
        <Loader2
          className="text-primary size-3.5 shrink-0 animate-spin"
          aria-hidden
        />
      ) : null}
      <span className="min-w-0 truncate font-medium text-foreground/90">
        {text}
      </span>
    </div>
  )
}

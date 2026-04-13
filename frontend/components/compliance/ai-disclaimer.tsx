"use client"

import * as React from "react"
import { TriangleAlert } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const STORAGE_KEY = "c401-d5-ai-disclaimer-dismissed"

export function AiDisclaimer({ className }: { className?: string }) {
  const [hidden, setHidden] = React.useState(false)

  React.useEffect(() => {
    try {
      if (localStorage.getItem(STORAGE_KEY) === "1") setHidden(true)
    } catch {
      /* private mode */
    }
  }, [])

  const dismiss = () => {
    try {
      localStorage.setItem(STORAGE_KEY, "1")
    } catch {
      /* ignore */
    }
    setHidden(true)
  }

  if (hidden) return null

  return (
    <div
      role="alert"
      className={cn(
        "border-amber-500/30 bg-amber-500/6 text-foreground flex flex-wrap items-start gap-2 rounded-md border px-2 py-1.5 sm:items-center sm:gap-2.5",
        className
      )}
    >
      <TriangleAlert
        className="text-amber-600 dark:text-amber-500 mt-0.5 size-3 shrink-0 sm:mt-0"
        aria-hidden
      />
      <p className="min-w-0 flex-1 text-[11px] leading-snug sm:text-xs">
        <span className="text-foreground font-semibold">C401 · D5 — AI · </span>
        Có thể sai; không thay tư vấn chính thức. Đối chiếu tài liệu nội bộ. Không nhập dữ liệu nhạy cảm.
      </p>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="text-muted-foreground h-6 shrink-0 px-2 text-[11px]"
        onClick={dismiss}
      >
        Ẩn
      </Button>
    </div>
  )
}

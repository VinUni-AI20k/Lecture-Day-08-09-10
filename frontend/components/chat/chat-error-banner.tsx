"use client"

import { AlertCircle } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

export function ChatErrorBanner({
  message,
  onDismiss,
  onRetry,
  className,
}: {
  message: string
  onDismiss: () => void
  onRetry: () => void
  className?: string
}) {
  return (
    <div
      role="alert"
      className={cn(
        "border-destructive/40 bg-destructive/10 text-destructive-foreground mx-3 flex flex-wrap items-center gap-2 rounded-lg border px-3 py-2 text-sm sm:mx-4",
        className
      )}
    >
      <AlertCircle className="size-4 shrink-0" aria-hidden />
      <p className="min-w-0 flex-1 text-xs leading-snug sm:text-sm">{message}</p>
      <div className="flex shrink-0 flex-wrap gap-1.5">
        <Button type="button" size="sm" variant="secondary" onClick={onRetry}>
          Thử lại
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={onDismiss}>
          Đóng
        </Button>
      </div>
    </div>
  )
}

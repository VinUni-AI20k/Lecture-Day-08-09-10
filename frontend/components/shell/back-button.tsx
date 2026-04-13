"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type BackButtonProps = {
  /** Dùng khi không có lịch sử (deep link) hoặc sau khi `router.back()` */
  fallbackHref: string
  label?: string
  className?: string
  variant?: React.ComponentProps<typeof Button>["variant"]
  size?: React.ComponentProps<typeof Button>["size"]
}

/**
 * Quay lại trang trước trong SPA; nếu không có history thì `router.push(fallbackHref)`.
 */
export function BackButton({
  fallbackHref,
  label = "Quay lại",
  className,
  variant = "ghost",
  size = "sm",
}: BackButtonProps) {
  const router = useRouter()

  return (
    <Button
      type="button"
      variant={variant}
      size={size}
      className={cn("gap-1.5", className)}
      onClick={() => {
        if (typeof window === "undefined") {
          router.push(fallbackHref)
          return
        }
        const ref = document.referrer
        const sameOrigin =
          ref !== "" &&
          (() => {
            try {
              return new URL(ref).origin === window.location.origin
            } catch {
              return false
            }
          })()
        if (sameOrigin && window.history.length > 1) {
          router.back()
          return
        }
        router.push(fallbackHref)
      }}
    >
      <ArrowLeft className="size-4 shrink-0" aria-hidden />
      {label}
    </Button>
  )
}

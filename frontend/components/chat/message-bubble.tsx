"use client"

import * as React from "react"
import ReactMarkdown from "react-markdown"

import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"

export function MessageBubble({
  role,
  children,
  variant = "default",
  className,
}: {
  role: "user" | "assistant"
  children: string
  /** Viền nhẹ khi độ tin cậy thấp (assistant). */
  variant?: "default" | "lowConfidence"
  className?: string
}) {
  const isUser = role === "user"
  const low = !isUser && variant === "lowConfidence"

  return (
    <div
      className={cn(
        "flex gap-3",
        isUser ? "flex-row-reverse" : "flex-row",
        className
      )}
    >
      <Avatar className="size-8 shrink-0 border border-border">
        <AvatarFallback
          className={cn(
            "text-xs font-medium",
            isUser ? "bg-primary text-primary-foreground" : "bg-muted"
          )}
        >
          {isUser ? "Bạn" : "AI"}
        </AvatarFallback>
      </Avatar>
      <div
        className={cn(
          "min-w-0 max-w-[min(100%,52rem)] rounded-lg border px-3 py-2 text-sm shadow-xs",
          isUser
            ? "bg-primary text-primary-foreground border-transparent"
            : "bg-card border-border",
          low &&
            "ring-amber-500/50 bg-amber-500/[0.06] ring-2 ring-offset-2 ring-offset-background"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap wrap-break-word">{children}</p>
        ) : (
          <div className="max-w-none space-y-2 text-sm leading-relaxed [&_a]:text-primary [&_a]:underline [&_p]:my-1">
            <ReactMarkdown
              components={{
                p: ({ children }) => (
                  <p className="wrap-break-word">{children}</p>
                ),
                strong: ({ children }) => (
                  <strong className="font-semibold">{children}</strong>
                ),
              }}
            >
              {children}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}

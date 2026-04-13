"use client"

import * as React from "react"
import { ThemeProvider } from "next-themes"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "@/components/ui/sonner"
import { AssistantStoreHydration } from "@/components/assistant-store-hydration"

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <div className="flex h-dvh w-full min-w-0 flex-col overflow-hidden">
        <AssistantStoreHydration />
        <TooltipProvider delayDuration={200}>
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            {children}
          </div>
        </TooltipProvider>
        <Toaster position="top-right" richColors closeButton />
      </div>
    </ThemeProvider>
  )
}

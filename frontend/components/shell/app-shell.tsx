"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { BotMessageSquare, Gauge, Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

const nav = [
  { href: "/", label: "Trợ lý", icon: BotMessageSquare },
  { href: "/pipeline", label: "Pipeline & quan sát", icon: Gauge },
] as const

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { setTheme } = useTheme()

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden md:flex-row">
      <aside
        className="border-border bg-card flex w-full shrink-0 flex-col border-b md:h-full md:w-56 md:shrink-0 md:border-r md:border-b-0"
        aria-label="Điều hướng chính"
      >
        <div className="flex items-center gap-2 border-b border-border px-4 py-3 md:flex-col md:items-stretch md:gap-3 md:border-b md:py-4">
          <div className="min-w-0 flex-1 md:px-0">
            <p className="truncate text-sm font-semibold tracking-tight">
              Trợ lý CS + IT
            </p>
            <p className="text-muted-foreground text-xs">Demo LangGraph pipeline</p>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="icon-sm"
                className="relative shrink-0"
                aria-label="Chọn giao diện sáng hoặc tối"
              >
                <Sun className="size-4 scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
                <Moon className="absolute size-4 scale-0 rotate-90 transition-all dark:rotate-0 dark:scale-100" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setTheme("light")}>
                Sáng
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTheme("dark")}>
                Tối
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTheme("system")}>
                Theo hệ thống
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-2 py-2 md:flex-col md:px-2">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = pathname === href
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
                aria-current={active ? "page" : undefined}
              >
                <Icon className="size-4 shrink-0 opacity-80" aria-hidden />
                {label}
              </Link>
            )
          })}
        </nav>
      </aside>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        {children}
      </div>
    </div>
  )
}

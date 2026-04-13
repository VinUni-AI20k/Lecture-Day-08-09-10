"use client"

import type { PipelineMetrics } from "@/lib/types/agent-events"
import { cn } from "@/lib/utils"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

function healthVariant(
  h: PipelineMetrics["schemaHealth"]
): "default" | "secondary" | "destructive" {
  if (h === "ok") return "default"
  if (h === "degraded") return "secondary"
  return "destructive"
}

export function PipelineMetricsStrip({
  metrics,
  className,
}: {
  metrics: PipelineMetrics | null
  className?: string
}) {
  return (
    <section
      className={cn("flex flex-col gap-2", className)}
      aria-label="Tín hiệu pipeline và dữ liệu"
    >
      <h2 className="text-sm font-semibold tracking-tight">
        Pipeline & quan sát (Day 10)
      </h2>
      {!metrics ? (
        <p className="text-muted-foreground text-xs">
          Chưa có tín hiệu — sẽ cập nhật khi mock gửi `pipeline_signal`.
        </p>
      ) : (
        <>
          {metrics.schemaHealth === "stale" ||
          (metrics.freshnessMinutes > 40 && metrics.schemaHealth !== "ok") ? (
            <Alert variant="destructive">
              <AlertTitle>Freshness cần chú ý</AlertTitle>
              <AlertDescription>
                Demo: coi như dữ liệu embedding hoặc ETL đang lệch SLA freshness
                (mock).
              </AlertDescription>
            </Alert>
          ) : null}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <Card className="shadow-none">
              <CardHeader className="pb-1">
                <CardTitle className="text-muted-foreground text-xs font-medium">
                  Freshness
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <p className="text-lg font-semibold tabular-nums">
                  {metrics.freshnessMinutes} phút
                </p>
                <p className="text-muted-foreground text-[10px]">
                  từ lần sync gần nhất (demo)
                </p>
              </CardContent>
            </Card>
            <Card className="shadow-none">
              <CardHeader className="pb-1">
                <CardTitle className="text-muted-foreground text-xs font-medium">
                  Volume 24h
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <p className="text-lg font-semibold tabular-nums">
                  {metrics.volume24h}
                </p>
                <p className="text-muted-foreground text-[10px]">
                  tài liệu / sự kiện (giả lập)
                </p>
              </CardContent>
            </Card>
            <Card className="shadow-none">
              <CardHeader className="pb-1">
                <CardTitle className="text-muted-foreground text-xs font-medium">
                  Schema
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-1 pt-0">
                <Badge variant={healthVariant(metrics.schemaHealth)}>
                  {metrics.schemaHealth}
                </Badge>
                {metrics.label ? (
                  <p className="text-muted-foreground text-[10px] leading-snug">
                    {metrics.label}
                  </p>
                ) : null}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </section>
  )
}

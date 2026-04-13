import Link from "next/link"
import { ArrowLeft } from "lucide-react"

import { BackButton } from "@/components/shell/back-button"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"

export default function PipelinePage() {
  return (
    <div className="bg-background flex min-h-0 flex-1 flex-col overflow-hidden">
      <header className="border-border shrink-0 border-b px-4 py-3">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <BackButton fallbackHref="/" label="Quay lại" />
          <Button variant="outline" size="sm" className="gap-1.5" asChild>
            <Link href="/">
              <ArrowLeft className="size-4" aria-hidden />
              Trợ lý
            </Link>
          </Button>
        </div>
        <h1 className="text-lg font-semibold tracking-tight">
          Pipeline & quan sát dữ liệu (Day 10)
        </h1>
        <p className="text-muted-foreground mt-1 max-w-2xl text-sm">
          Trang tham chiếu cho khối ETL/ELT, chất lượng dữ liệu và năm trụ quan
          sát (freshness, volume, distribution, schema, lineage). Trong demo
          chat, các chỉ số mock xuất hiện qua sự kiện{" "}
          <code className="bg-muted rounded px-1 py-0.5 font-mono text-xs">
            pipeline_signal
          </code>
          .
        </p>
      </header>
      <ScrollArea className="min-h-0 flex-1">
        <div className="mx-auto w-full max-w-3xl space-y-6 p-4 pb-8">
          <Card>
            <CardHeader>
              <CardTitle>Ingestion & orchestration</CardTitle>
              <CardDescription>
                CDC, retry/backoff, DLQ, DAG — áp dụng trước khi dữ liệu vào vector
                store phục vụ RAG.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-muted-foreground text-sm leading-relaxed">
              Khi backend Python (FastAPI + LangGraph) được thêm vào repo, pipeline
              thật có thể publish metric lên cùng contract SSE hoặc qua API quan
              sát tách biệt.
            </CardContent>
          </Card>
          <Separator />
          <Card>
            <CardHeader>
              <CardTitle>Data quality as code</CardTitle>
              <CardDescription>
                Expectation suite trong CI/CD — tránh “garbage in → garbage out”.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-muted-foreground text-sm leading-relaxed">
              Great Expectations hoặc tương đương; kết quả có thể map sang badge{" "}
              <code className="font-mono text-xs">schemaHealth</code> trong UI.
            </CardContent>
          </Card>
        </div>
      </ScrollArea>
    </div>
  )
}

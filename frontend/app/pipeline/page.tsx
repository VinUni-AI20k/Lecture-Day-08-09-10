import Link from "next/link"

import { BackButton } from "@/components/shell/back-button"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
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
        <div className="mb-3">
          <BackButton fallbackHref="/" label="Về trợ lý" />
        </div>
        <h1 className="text-lg font-semibold tracking-tight">
          Pipeline & quan sát dữ liệu (Day 10)
        </h1>
        <p className="text-muted-foreground mt-1 max-w-2xl text-sm leading-relaxed">
          Trang này tóm tắt <strong className="text-foreground font-medium">vì sao</strong>{" "}
          cần tầng dữ liệu trước khi tin vào câu trả lời của AI — và{" "}
          <strong className="text-foreground font-medium">cách demo</strong> hiển thị tín hiệu
          pipeline trong UI trợ lý.
        </p>
      </header>
      <ScrollArea className="min-h-0 flex-1">
        <div className="mx-auto w-full max-w-3xl space-y-6 p-4 pb-10">
          <Alert>
            <AlertTitle>Đọc trang này như thế nào?</AlertTitle>
            <AlertDescription className="text-sm leading-relaxed">
              Phần dưới lần lượt: (1) luồng dữ liệu vào RAG, (2) năm trụ quan sát, (3) sự kiện{" "}
              <code className="bg-muted rounded px-1 py-0.5 font-mono text-xs">
                pipeline_signal
              </code>{" "}
              mà mock SSE gửi, (4) chỗ hiển thị trên màn <strong>Trợ lý</strong>. Mở{" "}
              <Link
                href="/"
                className="text-primary font-medium underline-offset-4 hover:underline"
              >
                Trợ lý
              </Link>{" "}
              và gửi một câu hỏi để thấy panel &quot;Pipeline &amp; quan sát&quot; cập nhật sau các bước agent.
            </AlertDescription>
          </Alert>

          <Card>
            <CardHeader>
              <CardTitle>Dữ liệu đi vào RAG như thế nào?</CardTitle>
              <CardDescription>
                Từ nguồn (DB, ticket, PDF…) đến embedding — nếu đứt ở đây, model vẫn trả lời “nghe có vẻ đúng”.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-muted-foreground space-y-3 text-sm leading-relaxed">
              <ol className="list-decimal space-y-2 pl-5">
                <li>
                  <span className="text-foreground font-medium">Ingest</span> — lấy dữ liệu (CDC, API, batch),
                  giới hạn tốc độ, retry, hàng đợi lỗi (DLQ).
                </li>
                <li>
                  <span className="text-foreground font-medium">Transform</span> — làm sạch PII, chuẩn hoá
                  schema, gỡ trùng.
                </li>
                <li>
                  <span className="text-foreground font-medium">Validate / quality</span> — expectation (như
                  test) trước khi load.
                </li>
                <li>
                  <span className="text-foreground font-medium">Embed &amp; index</span> — vector hoá và ghi
                  vào store phục vụ retrieval trong demo đa agent.
                </li>
              </ol>
              <p>
                <strong className="text-foreground">Orchestration</strong> (DAG, Airflow/Prefect/…) đảm bảo
                thứ tự, idempotent, cảnh báo SLA — trùng với slide Day 10 trong khóa học.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Năm trụ quan sát (nhắc nhanh)</CardTitle>
              <CardDescription>
                Dùng để phát hiện “data sai trước khi đổ lỗi model”.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="text-muted-foreground grid gap-2 text-sm leading-relaxed sm:grid-cols-2">
                {[
                  ["Freshness", "Dữ liệu / index có còn mới so với nguồn?"],
                  ["Volume", "Số bản ghi, sự kiện có bất thường?"],
                  ["Distribution", "Phân bố giá trị có lệch (drift)?"],
                  ["Schema", "Cột, kiểu, null có đổi ngầm?"],
                  ["Lineage", "Bản ghi nào ảnh hưởng chunk nào trong RAG?"],
                ].map(([title, desc]) => (
                  <li
                    key={title}
                    className="bg-muted/40 flex flex-col gap-0.5 rounded-md border border-border/80 px-3 py-2"
                  >
                    <span className="text-foreground font-medium">{title}</span>
                    <span>{desc}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Sự kiện pipeline_signal trong demo SSE</CardTitle>
              <CardDescription>
                Sau các worker (retrieval, policy, synthesis), mock gửi một gói metric giả lập — UI đọc và vẽ
                thẻ Freshness / Volume / Schema.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-muted-foreground text-sm leading-relaxed">
                Backend thật (FastAPI + LangGraph) có thể phát cùng JSON qua stream; Next.js chỉ cần giữ đúng{" "}
                <code className="font-mono text-xs">type</code> và{" "}
                <code className="font-mono text-xs">metrics</code>.
              </p>
              <div className="bg-muted/60 overflow-x-auto rounded-md border p-3">
                <pre className="text-foreground font-mono text-xs leading-relaxed whitespace-pre-wrap">
{`{
  "type": "pipeline_signal",
  "metrics": {
    "freshnessMinutes": 12,
    "volume24h": 128,
    "schemaHealth": "ok",
    "label": "Pipeline ổn định"
  }
}`}
                </pre>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">schemaHealth: ok | degraded | stale</Badge>
                <Badge variant="outline">freshnessMinutes = phút từ lần sync gần nhất (demo)</Badge>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Trên màn Trợ lý, bạn sẽ thấy gì?</CardTitle>
              <CardDescription>
                Cột phải (desktop) hoặc nút Trace (mobile) — cùng một luồng với chat.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-muted-foreground space-y-2 text-sm leading-relaxed">
              <p>
                <strong className="text-foreground">Panel &quot;Pipeline &amp; quan sát&quot;</strong> nhận
                đúng sự kiện trên: cảnh báo nếu <code className="font-mono text-xs">stale</code>, badge schema,
                số phút freshness.
              </p>
              <p>
                Trước đó, trace liệt kê <strong className="text-foreground">supervisor → route → retrieval →
                policy → synthesis</strong>; panel RAG hiển thị chunk trích dẫn. Toàn bộ đến từ một luồng SSE
                — giống cách LangGraph stream updates theo node.
              </p>
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
              Great Expectations hoặc tương đương; kết quả có thể map sang{" "}
              <code className="font-mono text-xs">schemaHealth</code> hoặc cờ block index nếu fail nặng — UI
              chỉ phản ánh trạng thái mà pipeline báo.
            </CardContent>
          </Card>
        </div>
      </ScrollArea>
    </div>
  )
}

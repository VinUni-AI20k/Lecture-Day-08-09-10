import Link from "next/link";
import { ArrowRight, Layers, Zap, Search } from "lucide-react";
import { getRagApiBase } from "@/lib/rag-client";

export default function Home() {
  const api = getRagApiBase();

  return (
    <main className="mx-auto flex max-w-2xl flex-1 flex-col justify-center gap-10 px-6 py-20">
      {/* Hero */}
      <div className="space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
          <div className="h-1.5 w-1.5 rounded-full bg-primary" />
          Buổi 08 — Luồng RAG
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-foreground leading-tight">
          Hỏi đáp RAG{" "}
          <span className="text-primary">minh bạch luồng</span>
        </h1>
        <p className="text-base text-muted-foreground leading-relaxed">
          Trò chuyện với tài liệu đã lập chỉ mục; bảng theo dõi hiển thị từng bước
          truy xuất, ngữ cảnh được chọn, câu lệnh gửi AI và số liệu kỹ thuật (thời gian,
          chi phí ước lượng).
        </p>
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          {
            icon: Search,
            title: "Ngữ nghĩa / Từ khóa / Kết hợp",
            desc: "Chọn cách truy xuất phù hợp với từng loại câu hỏi.",
          },
          {
            icon: Layers,
            title: "Bảng Theo Dõi RAG",
            desc: "Xem từng bước xử lý — câu hỏi → truy xuất → sắp xếp lại → trả lời.",
          },
          {
            icon: Zap,
            title: "Số liệu thời gian thực",
            desc: "Thời gian, lượng token và chi phí ước tính cho mỗi lần gọi.",
          },
        ].map(({ icon: Icon, title, desc }) => (
          <div
            key={title}
            className="rounded-xl border border-border bg-card p-4 space-y-2"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Icon className="h-4 w-4 text-primary" />
            </div>
            <p className="text-sm font-semibold text-foreground">{title}</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {desc}
            </p>
          </div>
        ))}
      </div>

      {/* Setup steps */}
      <ol className="space-y-3">
        {[
          <>
            Chạy FastAPI trong thư mục lab (xem{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">
              README.md
            </code>
            ).
          </>,
          <>
            Tạo{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">
              .env.local
            </code>{" "}
            và đặt:{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">
              NEXT_PUBLIC_RAG_API_URL=http://127.0.0.1:8010
            </code>
          </>,
          <>
            Vào trang chat và đặt câu hỏi — ví dụ về SLA hoặc nội dung trong
            corpus.
          </>,
        ].map((step, i) => (
          <li key={i} className="flex items-start gap-3">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary mt-0.5">
              {i + 1}
            </span>
            <span className="text-sm text-muted-foreground leading-relaxed">
              {step}
            </span>
          </li>
        ))}
      </ol>

      {/* API info */}
      <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-3 py-2.5 text-xs text-muted-foreground">
        <div className="h-1.5 w-1.5 rounded-full bg-green-500 shrink-0" />
        <span>
          Điểm gọi API hiện tại:{" "}
          <code className="break-all text-foreground">{api}/api/rag</code>
        </span>
      </div>

      {/* CTA */}
      <div>
        <Link
          href="/chat"
          className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          Mở trò chuyện
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </main>
  );
}

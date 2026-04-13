import Link from "next/link";
import { getRagApiBase } from "@/lib/rag-client";

export default function Home() {
  const api = getRagApiBase();
  return (
    <main className="mx-auto flex max-w-lg flex-1 flex-col justify-center gap-6 px-6 py-16">
      <div>
        <p className="text-sm font-medium text-zinc-500">Day 08 Lab</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">
          RAG có minh bạch luồng
        </h1>
        <p className="mt-3 text-zinc-600 dark:text-zinc-400">
          Chat với tài liệu đã index; panel hiển thị từng bước retrieval và
          telemetry (thời gian, chi phí ước lượng).
        </p>
      </div>
      <ol className="list-decimal space-y-2 pl-5 text-sm text-zinc-700 dark:text-zinc-300">
        <li>Chạy FastAPI trong thư mục lab (xem README).</li>
        <li>
          Đặt <code className="rounded bg-zinc-100 px-1 dark:bg-zinc-800">NEXT_PUBLIC_RAG_API_URL</code>{" "}
          nếu API không ở cổng mặc định (hiện mặc định:{" "}
          <code className="break-all">{api}</code>).
        </li>
        <li>
          Vào trang chat và đặt câu hỏi — ví dụ về SLA hoặc nội dung trong
          corpus.
        </li>
      </ol>
      <Link
        href="/chat"
        className="inline-flex w-fit items-center justify-center rounded-xl bg-zinc-900 px-5 py-3 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
      >
        Mở chat
      </Link>
    </main>
  );
}

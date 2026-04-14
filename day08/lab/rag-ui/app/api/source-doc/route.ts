import { promises as fs } from "fs";
import path from "path";
import { NextRequest, NextResponse } from "next/server";

const DOCS_BASE = path.resolve(process.cwd(), "..", "data", "docs");

function guessContentType(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".pdf") return "application/pdf";
  if (ext === ".md") return "text/markdown; charset=utf-8";
  if (ext === ".txt") return "text/plain; charset=utf-8";
  if (ext === ".json") return "application/json; charset=utf-8";
  if (ext === ".csv") return "text/csv; charset=utf-8";
  return "application/octet-stream";
}

function toDocCandidates(src: string): string[] {
  const cleaned = src.replace(/^[/\\]+/, "");
  const ext = path.extname(cleaned).toLowerCase();
  const noExt = ext ? cleaned.slice(0, -ext.length) : cleaned;
  const normalized = noExt.replace(/[\\/]+/g, "_").replace(/-/g, "_").toLowerCase();

  // Ưu tiên đúng path trước, sau đó fallback theo tên chuẩn hóa trong data/docs.
  const candidates = [
    cleaned,
    `${noExt}.txt`,
    `${noExt}.md`,
    `${noExt}.pdf`,
    `${normalized}.txt`,
    `${normalized}.md`,
    `${normalized}.pdf`,
  ];
  return Array.from(new Set(candidates));
}

export async function GET(req: NextRequest) {
  try {
    const src = req.nextUrl.searchParams.get("src")?.trim();
    if (!src) {
      return NextResponse.json({ detail: "Thiếu tham số src" }, { status: 400 });
    }

    // Chặn path traversal
    if (src.includes("\0")) {
      return NextResponse.json({ detail: "Đường dẫn không hợp lệ" }, { status: 400 });
    }

    const docCandidates = toDocCandidates(src);
    let fullPath: string | null = null;

    for (const candidate of docCandidates) {
      const normalized = path.normalize(candidate).replace(/^([/\\])+/, "");
      const resolved = path.resolve(DOCS_BASE, normalized);
      if (!resolved.startsWith(DOCS_BASE)) continue;
      try {
        const st = await fs.stat(resolved);
        if (st.isFile()) {
          fullPath = resolved;
          break;
        }
      } catch {
        // try next candidate
      }
    }

    if (!fullPath) {
      return NextResponse.json(
        { detail: "Không tìm thấy tài liệu", requested: src },
        { status: 404 },
      );
    }

    const fileBuffer = await fs.readFile(fullPath);
    const contentType = guessContentType(fullPath);
    const fileName = path.basename(fullPath);

    return new NextResponse(fileBuffer, {
      status: 200,
      headers: {
        "content-type": contentType,
        "content-disposition": `inline; filename="${fileName}"`,
        "cache-control": "no-store",
      },
    });
  } catch {
    return NextResponse.json({ detail: "Không tìm thấy tài liệu" }, { status: 404 });
  }
}


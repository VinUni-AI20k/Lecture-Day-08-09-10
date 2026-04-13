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

    const normalized = path.normalize(src).replace(/^([/\\])+/, "");
    const fullPath = path.resolve(DOCS_BASE, normalized);
    if (!fullPath.startsWith(DOCS_BASE)) {
      return NextResponse.json({ detail: "Không được truy cập ngoài thư mục tài liệu" }, { status: 403 });
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


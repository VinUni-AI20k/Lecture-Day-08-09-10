import { NextRequest, NextResponse } from "next/server";

function getUpstreamBase(): string {
  const raw =
    (process.env.RAG_API_URL?.trim() ||
      process.env.NEXT_PUBLIC_RAG_API_URL?.trim() ||
      "http://127.0.0.1:8010").replace(/\/$/, "");
  return raw;
}

export async function POST(req: NextRequest) {
  const requestId = req.headers.get("x-request-id") ?? crypto.randomUUID();
  const upstream = `${getUpstreamBase()}/api/rag/abort`;
  try {
    const body = await req.text();
    const r = await fetch(upstream, {
      method: "POST",
      headers: { "content-type": "application/json", "x-request-id": requestId },
      body,
      cache: "no-store",
    });
    const text = await r.text();
    return new NextResponse(text, {
      status: r.status,
      headers: { "content-type": "application/json", "x-request-id": requestId },
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json(
      { ok: false, detail: msg },
      { status: 502 },
    );
  }
}

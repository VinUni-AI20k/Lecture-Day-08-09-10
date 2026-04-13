import { NextRequest, NextResponse } from "next/server";

function getUpstreamBase(): string {
  const fromPrivate = process.env.RAG_API_URL?.trim();
  const fromPublic = process.env.NEXT_PUBLIC_RAG_API_URL?.trim();
  const raw = fromPrivate || fromPublic || "http://127.0.0.1:8010";
  return raw.replace(/\/$/, "");
}

export async function POST(req: NextRequest) {
  const requestId = req.headers.get("x-request-id") ?? crypto.randomUUID();
  const upstream = `${getUpstreamBase()}/api/rag`;
  try {
    const body = await req.text();
    const r = await fetch(upstream, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-request-id": requestId,
      },
      body,
      cache: "no-store",
    });
    const text = await r.text();
    return new NextResponse(text, {
      status: r.status,
      headers: {
        "content-type": r.headers.get("content-type") || "application/json; charset=utf-8",
        "x-request-id": r.headers.get("x-request-id") || requestId,
      },
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json(
      {
        detail: `Proxy cannot reach FastAPI upstream (${upstream}). ${msg}`,
        request_id: requestId,
      },
      { status: 502, headers: { "x-request-id": requestId } },
    );
  }
}


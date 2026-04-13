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
  const upstream = `${getUpstreamBase()}/api/rag/stream`;

  try {
    const body = await req.text();
    const r = await fetch(upstream, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-request-id": requestId,
        accept: "text/event-stream",
      },
      body,
      // @ts-expect-error -- Node 18+ fetch supports duplex
      duplex: "half",
      cache: "no-store",
      signal: req.signal,
    });

    if (!r.ok || !r.body) {
      const text = await r.text();
      return new NextResponse(text, {
        status: r.status,
        headers: { "content-type": "application/json", "x-request-id": requestId },
      });
    }

    return new NextResponse(r.body, {
      status: 200,
      headers: {
        "content-type": "text/event-stream",
        "cache-control": "no-cache",
        "x-accel-buffering": "no",
        "x-request-id": r.headers.get("x-request-id") || requestId,
      },
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json(
      { detail: `Proxy cannot reach FastAPI upstream (${upstream}). ${msg}`, request_id: requestId },
      { status: 502, headers: { "x-request-id": requestId } },
    );
  }
}

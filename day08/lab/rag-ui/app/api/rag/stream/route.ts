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
      cache: "no-store",
      // Do NOT forward req.signal — avoids early disconnects in dev
    });

    if (!r.ok || !r.body) {
      const text = await r.text().catch(() => `HTTP ${r.status}`);
      return new NextResponse(text, {
        status: r.status,
        headers: { "content-type": "application/json", "x-request-id": requestId },
      });
    }

    // Explicitly pipe with ReadableStream to avoid Next.js dev-mode buffering.
    const upstreamReader = r.body.getReader();
    const echoedRid = r.headers.get("x-request-id") || requestId;

    const stream = new ReadableStream({
      async pull(controller) {
        try {
          const { done, value } = await upstreamReader.read();
          if (done) {
            controller.close();
          } else {
            controller.enqueue(value);
          }
        } catch (err) {
          controller.error(err);
        }
      },
      cancel() {
        upstreamReader.cancel().catch(() => {});
      },
    });

    return new NextResponse(stream, {
      status: 200,
      headers: {
        "content-type": "text/event-stream",
        "cache-control": "no-cache, no-transform",
        "x-accel-buffering": "no",
        "x-request-id": echoedRid,
        // Prevent Next.js from compressing the SSE stream
        "transfer-encoding": "chunked",
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

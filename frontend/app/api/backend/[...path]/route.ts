import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ path: string[] }> };

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  if (!path.length || !["run-pipeline", "approve-z-axis", "send-outreach"].includes(path.join("/"))) {
    return Response.json({ detail: "Unknown CareerOS backend route." }, { status: 404 });
  }

  const backend = (process.env.CAREEROS_BACKEND_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  const upstreamUrl = `${backend}/${path.map(encodeURIComponent).join("/")}`;
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");

  try {
    const upstream = await fetch(upstreamUrl, {
      method: "POST",
      headers,
      body: await request.arrayBuffer(),
      cache: "no-store",
      signal: request.signal,
    });
    const responseHeaders = new Headers(upstream.headers);
    responseHeaders.delete("content-length");
    responseHeaders.delete("connection");
    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return Response.json(
      { detail: "CareerOS backend is unreachable. Check CAREEROS_BACKEND_URL." },
      { status: 502 },
    );
  }
}

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  if (path.join("/") !== "outreach-analytics") {
    return Response.json({ detail: "Unknown CareerOS backend route." }, { status: 404 });
  }
  const backend = (process.env.CAREEROS_BACKEND_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  const upstream = await fetch(`${backend}/outreach-analytics`, {
    method: "GET",
    headers: { "X-CareerOS-Thread-ID": request.headers.get("X-CareerOS-Thread-ID") || "" },
    cache: "no-store",
    signal: request.signal,
  }).catch(() => null);
  if (!upstream) {
    return Response.json({ detail: "CareerOS backend is unreachable." }, { status: 502 });
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}
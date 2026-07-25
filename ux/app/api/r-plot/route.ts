import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const allowed = new Set(["seasonal", "restoration", "acoustic"]);
  const kind = String(body.kind || "");
  if (!allowed.has(kind)) {
    return NextResponse.json({ error: "Unknown plot family." }, { status: 400 });
  }
  const base = (process.env.R_SIDECAR_URL || "http://127.0.0.1:7331").replace(/\/$/, "");
  try {
    const response = await fetch(`${base}/plot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, data: body.data || [] }),
      signal: AbortSignal.timeout(30_000),
    });
    if (!response.ok) throw new Error(`r_sidecar_${response.status}`);
    const raw = (await response.json()) as Record<string, unknown>;
    const scalar = (value: unknown) => (Array.isArray(value) && value.length === 1 ? value[0] : value);
    return NextResponse.json({
      mode: "r",
      svg: scalar(raw.svg),
      note: scalar(raw.note),
      engine: scalar(raw.engine),
      session: scalar(raw.session),
    });
  } catch (error) {
    return NextResponse.json({
      mode: "browser",
      svg: null,
      note:
        "The R sidecar is offline. The same admitted rows remain visible in the browser figure; start the sidecar to reproduce the R rendering.",
      error: error instanceof Error ? error.message : "r_sidecar_unavailable",
    });
  }
}

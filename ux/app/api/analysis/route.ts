import { NextResponse } from "next/server";
import { previewResponse } from "@/lib/demo-response";
import { runCapability, runChat } from "@/lib/bridge";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const question = String(body.question || "").trim().slice(0, 8_000);
  if (!question) {
    return NextResponse.json({ error: "A question is required." }, { status: 400 });
  }
  try {
    if (body.capability_id) {
      const result = await runCapability(
        String(body.capability_id),
        typeof body.arguments === "object" && body.arguments ? body.arguments : {},
        question,
        String(body.request_id || crypto.randomUUID()),
      );
      return NextResponse.json({
        mode: "live",
        answer: result.envelope.answer?.headline || "The figure is ready.",
        focus: "site",
        results: [result],
        audit_id: result.envelope.audit?.audit_id,
      });
    }
    const session = String(body.session_id || `fieldnote-${crypto.randomUUID()}`).slice(0, 120);
    return NextResponse.json(await runChat(question, session));
  } catch (error) {
    const preview = previewResponse(question);
    return NextResponse.json({
      ...preview,
      note:
        preview.note ||
        "Preview mode: the local Valparai bridge is not reachable from this deployment.",
      bridge_error: error instanceof Error ? error.message : "bridge_unavailable",
    });
  }
}

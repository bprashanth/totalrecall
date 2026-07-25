import { readFile } from "node:fs/promises";
import type { AnalysisResponse, InlineResult, ResultEnvelope } from "./types";

const RESULT_MARKER = /<!--\s*idli-result:([\s\S]*?)-->/gi;

async function token(): Promise<string | null> {
  if (process.env.VALPARAI_BRIDGE_TOKEN) return process.env.VALPARAI_BRIDGE_TOKEN;
  const path = process.env.VALPARAI_BRIDGE_TOKEN_FILE;
  if (!path) return null;
  try {
    return (await readFile(path, "utf8")).trim();
  } catch {
    return null;
  }
}

function bridgeUrl(): string {
  return (process.env.VALPARAI_BRIDGE_URL || "http://172.17.0.1:7012").replace(/\/$/, "");
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  const bearer = await token();
  if (!bearer) throw new Error("bridge_not_configured");
  return fetch(`${bridgeUrl()}${path}`, {
    ...init,
    headers: {
      ...(init?.headers || {}),
      Authorization: `Bearer ${bearer}`,
    },
    signal: AbortSignal.timeout(180_000),
  });
}

async function inlineResult(resultId: string): Promise<InlineResult> {
  const response = await request(`/v1/results/${encodeURIComponent(resultId)}`);
  if (!response.ok) throw new Error(`result_${response.status}`);
  const envelope = (await response.json()) as ResultEnvelope;
  const payloads: Record<string, unknown> = {};
  for (const visual of envelope.visuals || []) {
    for (const layer of visual.layers || []) {
      const handle = layer.data_ref?.handle;
      if (!handle || payloads[handle]) continue;
      const payloadResponse = await request(
        `/v1/results/${encodeURIComponent(resultId)}/data/${encodeURIComponent(handle)}`,
      );
      if (payloadResponse.ok) {
        const type = payloadResponse.headers.get("content-type") || "";
        payloads[handle] = type.includes("json")
          ? await payloadResponse.json()
          : { media_type: type, unavailable_inline: true };
      }
    }
  }
  return { envelope, payloads };
}

function cleanAnswer(value: string): string {
  return value
    .replace(RESULT_MARKER, "")
    .replace(/<!--\s*idli-(?:insight|progress|activity|actions):[\s\S]*?-->/gi, "")
    .trim();
}

export async function runChat(question: string, sessionId: string): Promise<AnalysisResponse> {
  const response = await request("/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "idli-insight-valparai",
      session_id: sessionId,
      messages: [{ role: "user", content: question }],
      stream: false,
      idlisseus_context: { owner: "fieldnote", session_id: sessionId },
    }),
  });
  if (!response.ok) throw new Error(`bridge_chat_${response.status}`);
  const body = await response.json();
  const content = String(body?.choices?.[0]?.message?.content || "");
  const ids: string[] = [];
  for (const match of content.matchAll(RESULT_MARKER)) {
    try {
      const marker = JSON.parse(match[1]) as { result_id?: string };
      if (marker.result_id && !ids.includes(marker.result_id)) ids.push(marker.result_id);
    } catch {
      // A malformed presentation marker cannot become a result request.
    }
  }
  const results = await Promise.all(ids.map(inlineResult));
  const view = results.flatMap((item) => item.envelope.visuals || [])[0]?.view || "";
  const focus = /season/i.test(view)
    ? "seasonal"
    : /matrix/i.test(view)
      ? "acoustic"
      : /indicator|distribution/i.test(view)
        ? "restoration"
        : /effort/i.test(view)
          ? "effort"
          : /point|record/i.test(view)
            ? "records"
            : "site";
  return {
    mode: "live",
    answer: cleanAnswer(content),
    focus,
    results,
    audit_id: body?.codex_audit
      ? `${body.codex_audit.session_id}/${body.codex_audit.turn}`
      : undefined,
  };
}

export async function runCapability(
  capabilityId: string,
  args: Record<string, unknown>,
  question: string,
  requestId: string,
): Promise<InlineResult> {
  const response = await request("/v1/results/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      request_id: requestId,
      capability_id: capabilityId,
      arguments: args,
      question,
    }),
  });
  if (!response.ok) throw new Error(`capability_${response.status}`);
  const envelope = (await response.json()) as ResultEnvelope;
  return inlineResult(envelope.result_id);
}

export function bridgeConfigured(): Promise<boolean> {
  return token().then(Boolean);
}

export async function bridgeHealth(): Promise<{ live: boolean; skills?: number; model?: string }> {
  try {
    const response = await request("/health");
    if (!response.ok) return { live: false };
    const body = await response.json();
    return { live: true, skills: body.skills, model: body.model };
  } catch {
    return { live: false };
  }
}

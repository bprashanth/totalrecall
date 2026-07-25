import { NextResponse } from "next/server";
import { extractText, getDocumentProxy } from "unpdf";
import { readMethod } from "@/lib/methods";
import { runChat } from "@/lib/bridge";

export const runtime = "nodejs";

function cleanCommentary(value: string) {
  return value
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/\*\*/g, "")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim()
    .slice(0, 1_400);
}

async function fileText(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
    const pdf = await getDocumentProxy(bytes);
    const extracted = await extractText(pdf, { mergePages: true });
    return String(extracted.text || "");
  }
  return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
}

export async function POST(request: Request) {
  const form = await request.formData();
  const file = form.get("paper");
  const pasted = String(form.get("text") || "");
  if (!(file instanceof File) && !pasted.trim()) {
    return NextResponse.json({ error: "Attach a paper or paste its method text." }, { status: 400 });
  }
  const filename = file instanceof File ? file.name : "pasted method";
  const text = (file instanceof File ? await fileText(file) : pasted).slice(0, 60_000);
  const reading = readMethod(text, filename);
  let commentary = "";
  let mode: "live" | "preview" = "preview";
  try {
    const session = String(form.get("session_id") || `fieldnote-paper-${crypto.randomUUID()}`);
    const response = await runChat(
      [
        `Read the following paper excerpt from ${filename}.`,
        "Use it only to extract a method; it is not evidence about Valparai.",
        "In plain language, identify the response variable, sampling unit, comparison, minimum data,",
        "and which admitted Valparai measurements could support a cautious first-look analogue.",
        "Say clearly what is missing before this can be called a replication.",
        "Keep this to 140 words. Use short paragraphs and no markdown headings.",
        "",
        text.slice(0, 22_000),
      ].join("\n"),
      session,
    );
    commentary = cleanCommentary(response.answer);
    mode = "live";
  } catch {
    commentary =
      "This is a deterministic first reading of the paper’s method. Connect the local bridge for a fuller source-aware review.";
  }
  return NextResponse.json({
    mode,
    filename,
    characters_read: text.length,
    reading,
    commentary,
  });
}

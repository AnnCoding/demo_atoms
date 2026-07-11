export const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8010";

export type SSEEvent = {
  type:
    | "phase"
    | "delta"
    | "tool_call"
    | "tool_result"
    | "approval"
    | "done"
    | "error";
  [k: string]: unknown;
};

/** 读 SSE 流(POST)。EventSource 不支持 POST,故用 fetch + ReadableStream。 */
export async function runStream(
  path: string,
  body: Record<string, unknown>,
  onEvent: (e: SSEEvent) => void,
  signal?: AbortSignal,
) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() || "";
    for (const p of parts) {
      const line = p.split("\n").find((l) => l.startsWith("data: "));
      if (line) onEvent(JSON.parse(line.slice(6)));
    }
  }
}

export async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  return r.json();
}

export async function uploadFile(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${API}/api/upload`, { method: "POST", body: fd });
  return r.json();
}

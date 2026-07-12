"use client";
import { useRef, useState } from "react";
import { runStream } from "@/lib/api";
import PreviewFrame from "@/components/PreviewFrame";

type Msg = {
  id?: string;
  role: string;
  agent: string;
  text?: string;
  content?: string;
  format?: string;
  created_at?: number;
};

function ChatBubble({ m }: { m: Msg }) {
  const content = m.content || m.text || "";
  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] px-3 py-1.5 rounded-2xl rounded-br-sm bg-blue-600 text-white text-xs whitespace-pre-wrap">
          {content}
        </div>
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs shadow-sm">
      <div className="mb-1 flex items-center gap-2">
        <span className="font-semibold text-blue-700">
          {m.agent || "AI 团队"}
        </span>
        {m.format && (
          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500">
            {m.format}
          </span>
        )}
      </div>
      <div className="max-h-40 overflow-auto whitespace-pre-wrap leading-relaxed text-gray-700">
        {content}
      </div>
    </div>
  );
}

export default function ProjectViewer({
  slug,
  idea,
  initialCode,
  files,
  conversation,
}: {
  slug: string;
  idea: string;
  initialCode: string;
  files: string[];
  conversation: Msg[];
}) {
  const [msgs, setMsgs] = useState<Msg[]>(conversation);
  const [code, setCode] = useState(initialCode);
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("");
  const pendingRef = useRef("");

  const send = async () => {
    if (!input.trim() || running) return;
    const msg = input.trim();
    pendingRef.current = msg;
    setInput("");
    setRunning(true);
    setStatus("正在修改…");
    setMsgs((prev) => [...prev, { role: "user", agent: "", text: msg }]);
    setCode(""); // 迭代从空白流式刷新预览
    await runStream("/api/chat", { slug, message: msg }, (e) => {
      const t = e.type as string;
      if (t === "phase") setStatus(`${e.agent} ${e.role || ""}…`);
      else if (t === "delta")
        setCode((prev) => prev + ((e.text as string) || ""));
      else if (t === "validate")
        setStatus(e.ok ? "运行校验通过" : "校验报错,自愈修复中…");
      else if (t === "done") {
        const iter = (e.iteration as number) || 1;
        setMsgs((prev) => [
          ...prev,
          {
            role: "assistant",
            agent: "Alex",
            text: `✅ 已完成第 ${iter} 轮迭代修改`,
          },
        ]);
        setRunning(false);
        setStatus("");
      } else if (t === "error") {
        setStatus((e.message as string) || "出错");
        setRunning(false);
      }
    });
  };

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col">
      <div className="px-4 py-2 border-b bg-white text-sm text-gray-700 truncate flex items-center gap-2">
        <span className="font-medium truncate">{idea || "生成应用"}</span>
        {status && (
          <span className="ml-auto text-xs text-gray-400 shrink-0">
            {status}
          </span>
        )}
      </div>
      <div className="flex-1 grid grid-cols-[320px_1fr] divide-x overflow-hidden">
        {/* 左:对话历史 + 继续对话 */}
        <div className="flex flex-col overflow-hidden bg-gray-50">
          <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase border-b">
            💬 生成对话
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {msgs.length === 0 ? (
              <div className="text-xs text-gray-400">（暂无对话）</div>
            ) : (
              msgs.map((m, i) => <ChatBubble key={i} m={m} />)
            )}
            {running && (
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <span className="inline-block w-3 h-3 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
                {status}
              </div>
            )}
          </div>
          {/* 继续对话输入框:基于本作品迭代,更新作品 code + 对话 */}
          <div className="border-t p-2 flex gap-2 bg-white">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              disabled={running}
              placeholder="继续对话,如:把按钮改成红色 / 加个导出功能"
              className="flex-1 px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-40"
            />
            <button
              onClick={send}
              disabled={running || !input.trim()}
              className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40"
            >
              发送
            </button>
          </div>
        </div>
        {/* 右:预览(多文件时带文件树) */}
        <div className="flex flex-col overflow-hidden">
          {files.length > 0 ? (
            <div className="flex-1 grid grid-cols-[200px_1fr] divide-x overflow-hidden">
              <div className="overflow-y-auto p-3 bg-white">
                <div className="text-xs font-semibold text-gray-400 uppercase mb-2">
                  文件 ({files.length})
                </div>
                <ul className="space-y-0.5">
                  {files.map((f) => (
                    <li
                      key={f}
                      className="text-xs font-mono text-gray-700 truncate"
                      title={f}
                    >
                      📄 {f}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="overflow-hidden">
                <PreviewFrame html={code} slug={slug} />
              </div>
            </div>
          ) : (
            <div className="flex-1">
              <PreviewFrame html={code} slug={slug} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

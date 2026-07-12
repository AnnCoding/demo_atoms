"use client";
import { useEffect, useRef } from "react";
import type { Msg } from "@/lib/types";

export default function ChatPanel({ messages }: { messages: Msg[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="h-full overflow-y-auto p-3 space-y-2">
      {messages.length === 0 && (
        <div className="text-gray-400 text-sm">
          对话与 Agent 活动将显示在这里…
        </div>
      )}
      {messages.map((m) => {
        // 用户消息:右对齐蓝色气泡
        if (m.kind === "user") {
          return (
            <div key={m.id} className="flex justify-end">
              <div className="max-w-[85%] px-3 py-1.5 rounded-2xl rounded-br-sm bg-blue-600 text-white text-sm whitespace-pre-wrap">
                {m.text}
              </div>
            </div>
          );
        }
        // 完成总结:绿色卡片
        if (m.kind === "summary") {
          return (
            <div
              key={m.id}
              className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm"
            >
              <div className="font-semibold text-green-700 mb-1">
                {m.emoji} {m.role || "完成"}
              </div>
              <div className="text-green-800 whitespace-pre-wrap">{m.text}</div>
            </div>
          );
        }
        // 正在编写代码:带 spinner 的占位
        if (m.kind === "coding") {
          return (
            <div
              key={m.id}
              className="flex items-center gap-2 text-sm text-gray-500"
            >
              <span className="inline-block w-3 h-3 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
              {m.emoji && <span>{m.emoji}</span>}
              <span>{m.text}</span>
            </div>
          );
        }
        // phase / delta / tool
        const isPhase = m.kind === "phase";
        const isTool = m.kind === "tool";
        if (isTool) {
          return (
            <details
              key={m.id}
              className="rounded-lg border border-gray-200 bg-gray-50 text-xs"
            >
              <summary className="cursor-pointer px-3 py-2 text-gray-700">
                🔧 {m.agent ? `${m.agent} · ` : ""}
                {m.text}
              </summary>
              {m.payload && (
                <pre className="max-h-56 overflow-auto border-t bg-white p-3 text-[11px] leading-relaxed text-gray-600">
                  {JSON.stringify(m.payload, null, 2)}
                </pre>
              )}
            </details>
          );
        }
        if (isPhase) {
          return (
            <div
              key={m.id}
              className="rounded-lg border border-blue-100 bg-blue-50 p-3"
            >
              <div className="flex items-center gap-2 text-sm font-semibold text-blue-800">
                <span>{m.emoji}</span>
                <span>{m.agent}</span>
                <span className="font-normal text-blue-500">{m.role}</span>
              </div>
              <div className="mt-1 text-xs text-blue-700">{m.text}</div>
            </div>
          );
        }
        if (m.kind === "decision") {
          return (
            <div
              key={m.id}
              className="rounded-lg border border-violet-100 bg-violet-50 p-3 text-xs"
            >
              <div className="font-semibold text-violet-800">
                {m.emoji} {m.agent} · {m.role}
              </div>
              <div className="mt-1 text-violet-700">{m.text}</div>
              {m.payload && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {Object.entries(m.payload).map(([key, value]) => (
                    <span
                      key={key}
                      className="rounded bg-white px-2 py-1 text-[10px] text-violet-600"
                    >
                      {key}:{" "}
                      {Array.isArray(value)
                        ? value.join(", ")
                        : String(value ?? "")}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        }
        if (m.kind === "error") {
          return (
            <div
              key={m.id}
              className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"
            >
              <div className="font-semibold">
                {m.emoji} {m.agent} · {m.role}
              </div>
              <div className="mt-1 whitespace-pre-wrap">{m.text}</div>
            </div>
          );
        }
        return (
          <div key={m.id} className={"text-sm " + "text-gray-800"}>
            <span className={m.kind === "delta" ? "whitespace-pre-wrap" : ""}>
              {m.text}
            </span>
          </div>
        );
      })}
      <div ref={endRef} />
    </div>
  );
}

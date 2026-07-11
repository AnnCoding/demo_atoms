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
        return (
          <div
            key={m.id}
            className={
              "text-sm " +
              (isPhase
                ? "font-semibold text-blue-600 border-l-2 border-blue-400 pl-2"
                : isTool
                  ? "text-gray-500 italic"
                  : "text-gray-800")
            }
          >
            {isPhase && <span className="mr-1">{m.emoji}</span>}
            {isPhase ? `${m.agent}(${m.role}) · ` : isTool ? "🔧 " : ""}
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

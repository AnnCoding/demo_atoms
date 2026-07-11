"use client";
import { useEffect, useState, type ReactNode } from "react";

const TABS = [
  { k: "plan", label: "🧑‍💼 计划" },
  { k: "spec", label: "📋 规格" },
  { k: "arch", label: "🏗 架构" },
  { k: "report", label: "🔬 报告" },
  { k: "code", label: "⚙️ 代码" },
  { k: "review", label: "✅ 验收" },
];

// 行内渲染:**加粗** 和 `行内代码`
function inline(s: string, k: { i: number }): ReactNode {
  const parts: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(s))) {
    if (m.index > last) parts.push(s.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**"))
      parts.push(
        <strong key={k.i++} className="font-semibold text-gray-900">
          {tok.slice(2, -2)}
        </strong>,
      );
    else
      parts.push(
        <code
          key={k.i++}
          className="bg-gray-100 text-pink-600 px-1 py-0.5 rounded text-[11px] font-mono"
        >
          {tok.slice(1, -1)}
        </code>,
      );
    last = m.index + tok.length;
  }
  if (last < s.length) parts.push(s.slice(last));
  return parts;
}

// 简易 markdown 渲染(标题/列表/代码块/段落),不引入依赖
function renderMarkdown(md: string): ReactNode {
  const lines = md.split("\n");
  const out: ReactNode[] = [];
  const k = { i: 0 };
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    // 代码块 ```
    if (line.trim().startsWith("```")) {
      const buf: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        buf.push(lines[i]);
        i++;
      }
      i++; // 跳过结束 ```
      out.push(
        <pre
          key={k.i++}
          className="bg-gray-800 text-gray-100 rounded-md p-2 my-1.5 overflow-x-auto text-[11px] leading-relaxed font-mono"
        >
          <code>{buf.join("\n")}</code>
        </pre>,
      );
      continue;
    }
    // 表格行(简单按 | 分隔,粗略渲染)
    if (/^\s*\|.*\|\s*$/.test(line) && out.length > 0) {
      const cells = line
        .split("|")
        .map((c) => c.trim())
        .filter(Boolean);
      out.push(
        <div
          key={k.i++}
          className="flex gap-2 text-[11px] text-gray-600 py-0.5 border-b border-gray-100"
        >
          {cells.map((c, idx) => (
            <span key={idx} className="flex-1">
              {inline(c, k)}
            </span>
          ))}
        </div>,
      );
      i++;
      continue;
    }
    // 标题 # ## ### ####
    const hm = line.match(/^(#{1,4})\s+(.*)/);
    if (hm) {
      const lvl = hm[1].length;
      const sizes = ["text-sm", "text-sm", "text-xs", "text-xs"];
      out.push(
        <div
          key={k.i++}
          className={`font-bold text-gray-800 mt-2.5 ${sizes[lvl - 1] || "text-xs"}`}
        >
          {inline(hm[2], k)}
        </div>,
      );
      i++;
      continue;
    }
    // 无序/有序列表
    const lm = line.match(/^\s*([-*]|\d+\.)\s+(.*)/);
    if (lm) {
      const isNum = /\d+\./.test(lm[1]);
      out.push(
        <div
          key={k.i++}
          className="ml-3 text-gray-700 leading-relaxed flex gap-1.5"
        >
          <span className="text-gray-400 select-none">
            {isNum ? `${lm[1]} ` : "•"}
          </span>
          <span>{inline(lm[2], k)}</span>
        </div>,
      );
      i++;
      continue;
    }
    // 空行跳过
    if (!line.trim()) {
      i++;
      continue;
    }
    // 段落
    out.push(
      <div key={k.i++} className="text-gray-700 leading-relaxed my-0.5">
        {inline(line, k)}
      </div>,
    );
    i++;
  }
  return out;
}

// JSON 美化 + 语法着色;非 JSON 返回 null
function renderJson(text: string): ReactNode | null {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null) return null;
  const pretty = JSON.stringify(data, null, 2);
  const html = pretty
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(
      /("(?:[^"\\]|\\.)*")(\s*:)/g,
      '<span class="text-blue-600">$1</span>$2',
    )
    .replace(
      /:\s*("(?:[^"\\]|\\.)*")/g,
      ': <span class="text-green-600">$1</span>',
    )
    .replace(
      /:\s*(true|false)/g,
      ': <span class="text-purple-600 font-medium">$1</span>',
    )
    .replace(/:\s*(null)/g, ': <span class="text-gray-400">$1</span>')
    .replace(/:\s*(-?\d+\.?\d*)/g, ': <span class="text-orange-600">$1</span>');
  return (
    <pre
      className="text-[11px] leading-relaxed font-mono whitespace-pre-wrap"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function renderBody(tab: string, content: string | undefined): ReactNode {
  if (!content) return <div className="text-gray-400 text-xs">（暂无）</div>;
  if (tab === "code")
    return (
      <pre className="text-[11px] leading-relaxed font-mono whitespace-pre-wrap text-gray-800">
        {content}
      </pre>
    );
  // 先试 JSON(spec/plan/triage 多为 JSON),失败当 markdown
  const json = renderJson(content);
  if (json) return json;
  return <div className="space-y-0.5">{renderMarkdown(content)}</div>;
}

export default function ArtifactPanel({
  artifacts,
}: {
  artifacts: Record<string, string>;
}) {
  const [tab, setTab] = useState("plan");

  useEffect(() => {
    if (!artifacts[tab]) {
      const next = TABS.find((t) => artifacts[t.k]);
      if (next) setTab(next.k);
    }
  }, [artifacts, tab]);

  return (
    <div className="h-full flex flex-col">
      <div className="flex border-b flex-wrap">
        {TABS.map((t) => (
          <button
            key={t.k}
            onClick={() => artifacts[t.k] && setTab(t.k)}
            disabled={!artifacts[t.k]}
            className={
              "px-2.5 py-1.5 text-xs border-b-2 " +
              (tab === t.k
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-400") +
              (!artifacts[t.k] ? " opacity-30 cursor-not-allowed" : "")
            }
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-3 text-xs">
        {renderBody(tab, artifacts[tab])}
      </div>
    </div>
  );
}

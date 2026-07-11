"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getJSON, runStream, uploadFile } from "@/lib/api";
import type { AgentInfo, Approval, ModeInfo, Msg } from "@/lib/types";
import ChatPanel from "@/components/ChatPanel";
import AgentTeam from "@/components/AgentTeam";
import ArtifactPanel from "@/components/ArtifactPanel";
import PreviewFrame from "@/components/PreviewFrame";
import ApprovalCard from "@/components/ApprovalCard";
import ModeSwitch from "@/components/ModeSwitch";
import AttachmentUpload from "@/components/AttachmentUpload";

const ARTIFACT_LABELS: Record<string, string> = {
  code: "编写代码",
  spec: "整理需求规格",
  arch: "设计技术架构",
  review: "做最终验收",
  report: "撰写调研报告",
  triage: "分析需求",
  plan: "制定计划",
};

export default function Home() {
  const [modes, setModes] = useState<ModeInfo[]>([]);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [mode, setMode] = useState("team");
  const [idea, setIdea] = useState("");
  const [attachments, setAttachments] = useState<
    { id: string; filename: string; kind: string }[]
  >([]);

  const [running, setRunning] = useState(false);
  const [started, setStarted] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [currentAgent, setCurrentAgent] = useState("");
  const [completed, setCompleted] = useState<string[]>([]);
  const [artifacts, setArtifacts] = useState<Record<string, string>>({});
  const [approval, setApproval] = useState<Approval | null>(null);
  const [clarify, setClarify] = useState<{
    questions: string[];
    sessionId: string;
  } | null>(null);
  const [clarifyAns, setClarifyAns] = useState("");
  const [shareUrl, setShareUrl] = useState("");
  const [files, setFiles] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [previewHtml, setPreviewHtml] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [chatInput, setChatInput] = useState("");

  const idRef = useRef(0);
  const curArt = useRef("");
  const codeRef = useRef("");
  const lastPreview = useRef(0);

  useEffect(() => {
    codeRef.current = artifacts.code || "";
    const now = Date.now();
    if (now - lastPreview.current > 800) {
      lastPreview.current = now;
      setPreviewHtml(codeRef.current);
    }
  }, [artifacts.code]);

  useEffect(() => {
    getJSON<{ modes: ModeInfo[] }>("/api/modes").then((r) => {
      setModes(r.modes);
      if (r.modes[1]) setMode(r.modes[1].id);
    });
    getJSON<{ agents: AgentInfo[] }>("/api/agents").then((r) =>
      setAgents(r.agents),
    );
  }, []);

  const push = (m: Omit<Msg, "id">) =>
    setMessages((prev) => [...prev, { ...m, id: ++idRef.current }]);

  const onEvent = (e: Record<string, unknown>) => {
    const t = e.type as string;
    if (t === "phase") {
      setCurrentAgent(e.agent as string);
      curArt.current = (e.artifact as string) || "";
      push({
        agent: e.agent as string,
        emoji: (e.emoji as string) || "",
        role: (e.role as string) || "",
        kind: "phase",
        text: `${e.role} 开始工作`,
      });
    } else if (t === "delta") {
      const key = curArt.current;
      if (key)
        setArtifacts((prev) => ({
          ...prev,
          [key]: (prev[key] || "") + (e.text as string),
        }));
      // 所有 artifact 原文都不进对话区(避免 JSON/markdown/代码刷屏),
      // 只显示一次"正在产出"占位;完整内容请看右侧工件面板
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (
          last &&
          last.kind === "coding" &&
          last.agent === (e.agent as string)
        )
          return prev;
        const label = ARTIFACT_LABELS[key] || "产出内容";
        return [
          ...prev,
          {
            id: ++idRef.current,
            agent: (e.agent as string) || "",
            emoji: "✍️",
            role: "",
            kind: "coding",
            text: `${e.agent || "Agent"} 正在${label}…`,
          },
        ];
      });
    } else if (t === "tool_call") {
      const a = e.args as object;
      push({
        agent: (e.agent as string) || "",
        emoji: "🔧",
        role: "",
        kind: "tool",
        text: `调用 ${e.tool}(${Object.keys(a || {}).join(",")})`,
      });
    } else if (t === "tool_result") {
      push({
        agent: "",
        emoji: "↳",
        role: "",
        kind: "tool",
        text: String(e.result || "").slice(0, 200),
      });
    } else if (t === "validate") {
      const ok = e.ok as boolean;
      push({
        agent: "校验器",
        emoji: ok ? "✅" : "⚠️",
        role: "",
        kind: "tool",
        text: ok
          ? `运行时校验通过${e.skipped ? "(已跳过)" : ""}`
          : `第 ${(Number(e.attempt) || 0) + 1} 次校验报错,触发自愈: ${String(e.errors || "").slice(0, 140)}`,
      });
    } else if (t === "routed") {
      const parts = [`🧭 需求分析完成 · 复杂度: ${e.complexity}`];
      if (e.summary)
        parts.push(`\n💡 我理解的需求: ${(e.summary as string).trim()}`);
      if (e.plan) parts.push(`\n📋 执行计划:\n${(e.plan as string).trim()}`);
      push({
        agent: "Mike",
        emoji: "🧭",
        role: "需求分析",
        kind: "delta",
        text: parts.join(""),
      });
    } else if (t === "clarify") {
      const qs = (e.questions as string[]) || [];
      setClarify({ questions: qs, sessionId: e.session_id as string });
      // Mike 的提问也进对话历史(弹窗之外,左栏保留完整对话流)
      push({
        agent: "Mike",
        emoji: "🧑‍💼",
        role: "需求澄清",
        kind: "delta",
        text:
          "在开工前,我想先和你确认几个关键细节:\n" +
          qs.map((q) => "• " + q).join("\n"),
      });
    } else if (t === "approval") {
      setApproval({
        artifact: e.artifact as string,
        value: e.value as string,
        sessionId: e.session_id as string,
      });
      setArtifacts((prev) => ({
        ...prev,
        [e.artifact as string]: e.value as string,
      }));
      if (currentAgent) setCompleted((c) => [...new Set([...c, currentAgent])]);
    } else if (t === "done") {
      if (currentAgent) setCompleted((c) => [...new Set([...c, currentAgent])]);
      setPreviewHtml(codeRef.current);
      setFiles((e.files as string[]) || []);
      setShareUrl(e.shareUrl as string);
      if (e.session_id) setSessionId(e.session_id as string);
      if (e.summary)
        push({
          agent: "",
          emoji: "✅",
          role: e.iteration ? `第 ${e.iteration} 轮迭代完成` : "本次完成",
          kind: "summary",
          text: e.summary as string,
        });
      setRunning(false);
    } else if (t === "error") {
      setError((e.message as string) || "未知错误");
      setRunning(false);
    }
  };

  const start = async () => {
    if (!idea.trim()) return;
    setRunning(true);
    setStarted(true);
    setError("");
    setShareUrl("");
    setMessages([]);
    setArtifacts({});
    setSessionId("");
    setChatInput("");
    setApproval(null);
    setClarify(null);
    setCompleted([]);
    setCurrentAgent("");
    setPreviewHtml("");
    setFiles([]);
    codeRef.current = "";
    lastPreview.current = 0;
    await runStream(
      "/api/generate",
      {
        mode,
        prompt: idea,
        attachment_ids: attachments.map((a) => a.id),
      },
      onEvent,
    );
  };

  const approve = async () => {
    if (!approval) return;
    if (currentAgent) setCompleted((c) => [...new Set([...c, currentAgent])]);
    setApproval(null);
    setRunning(true);
    await runStream(
      "/api/approve",
      { session_id: approval.sessionId },
      onEvent,
    );
  };

  const submitClarify = async () => {
    if (!clarify) return;
    const ans = clarifyAns;
    push({ agent: "你", emoji: "", role: "", kind: "user", text: ans });
    setClarify(null);
    setClarifyAns("");
    setRunning(true);
    await runStream(
      "/api/approve",
      { session_id: clarify.sessionId, answers: ans },
      onEvent,
    );
  };

  const sendChat = async () => {
    if (!chatInput.trim() || !sessionId) return;
    const msg = chatInput.trim();
    push({ agent: "你", emoji: "", role: "", kind: "user", text: msg });
    setChatInput("");
    setRunning(true);
    setError("");
    // 迭代从空白流式刷新预览
    setArtifacts((prev) => ({ ...prev, code: "" }));
    codeRef.current = "";
    setPreviewHtml("");
    await runStream(
      "/api/chat",
      { session_id: sessionId, message: msg },
      onEvent,
    );
  };

  const onUpload = async (file: File) => {
    try {
      const r = await uploadFile(file);
      setAttachments((prev) => [
        ...prev,
        { id: r.attachment_id, filename: r.filename, kind: r.kind },
      ]);
    } catch {
      setError("附件上传失败");
    }
  };

  const reset = () => {
    setStarted(false);
    setRunning(false);
    setIdea("");
    setAttachments([]);
    setMessages([]);
    setArtifacts({});
    setCompleted([]);
    setCurrentAgent("");
    setSessionId("");
    setChatInput("");
    setShareUrl("");
    setFiles([]);
    setPreviewHtml("");
  };

  if (!started) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16">
        <h1 className="text-3xl font-bold mb-2">
          ⚡ 你的 AI 团队,把想法变成应用
        </h1>
        <p className="text-gray-500 mb-8">
          告诉它你想做什么,智能体团队接力生成可运行的应用。
        </p>
        <textarea
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="例:一个帮我记录每日开销的记账小工具…"
          className="w-full h-32 p-3 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <div className="mt-4">
          <div className="text-xs text-gray-400 mb-1">模式</div>
          <ModeSwitch modes={modes} value={mode} onChange={setMode} />
        </div>
        <div className="mt-4">
          <div className="text-xs text-gray-400 mb-1">附件(可选)</div>
          <AttachmentUpload
            attachments={attachments}
            onUpload={onUpload}
            onRemove={(id) =>
              setAttachments((p) => p.filter((a) => a.id !== id))
            }
          />
        </div>
        {error && <div className="mt-4 text-sm text-red-500">{error}</div>}
        <button
          onClick={start}
          disabled={!idea.trim() || running}
          className="mt-6 w-full py-3 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-40"
        >
          {running ? "启动中…" : "开始构建 →"}
        </button>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col">
      <ApprovalCard approval={approval} onApprove={approve} />
      {clarify && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full flex flex-col">
            <div className="px-5 py-3 border-b font-semibold">
              🧑‍💼 Mike 想和你确认几个细节
            </div>
            <div className="px-5 py-3 space-y-1 text-sm text-gray-700">
              {clarify.questions.map((q, i) => {
                const text =
                  typeof q === "string"
                    ? q
                    : (q as { question?: string })?.question ||
                      JSON.stringify(q);
                return <div key={i}>• {text}</div>;
              })}
            </div>
            <textarea
              value={clarifyAns}
              onChange={(e) => setClarifyAns(e.target.value)}
              placeholder="逐条回答…"
              className="mx-5 my-3 h-28 p-3 border rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <div className="px-5 py-3 border-t flex justify-end gap-2">
              <button
                onClick={() => {
                  setClarify(null);
                  setRunning(false);
                }}
                className="px-4 py-1.5 text-sm rounded-lg border border-gray-300 text-gray-500"
              >
                跳过
              </button>
              <button
                onClick={submitClarify}
                disabled={!clarifyAns.trim()}
                className="px-4 py-1.5 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40"
              >
                提交回答 →
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="border-b bg-white px-4 py-2 flex items-center gap-3">
        <button
          onClick={reset}
          className="text-sm text-gray-500 hover:text-blue-600"
        >
          ← 新建
        </button>
        <span className="text-sm text-gray-700 truncate max-w-md">{idea}</span>
        <span className="ml-auto text-xs px-2 py-1 rounded bg-gray-100">
          {modes.find((m) => m.id === mode)?.emoji}{" "}
          {modes.find((m) => m.id === mode)?.name}
        </span>
        {files.length > 0 && (
          <span className="text-xs px-2 py-1 rounded bg-purple-100 text-purple-700">
            🧩 多文件({files.length})
          </span>
        )}
        {shareUrl && files.length === 0 && (
          <Link
            href={shareUrl}
            target="_blank"
            className="text-xs px-3 py-1 rounded bg-green-600 text-white hover:bg-green-700"
          >
            ✓ 打开应用 ↗
          </Link>
        )}
      </div>
      {error && (
        <div className="bg-red-50 text-red-600 text-sm px-4 py-1">{error}</div>
      )}
      <div className="flex-1 grid grid-cols-[1fr_1.3fr_0.9fr] divide-x overflow-hidden">
        <div className="flex flex-col overflow-hidden bg-white">
          <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase border-b">
            对话
          </div>
          <div className="flex-1 overflow-hidden">
            <ChatPanel messages={messages} />
          </div>
          <div className="border-t p-2 flex gap-2">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendChat();
                }
              }}
              disabled={running || !sessionId}
              placeholder={
                sessionId
                  ? running
                    ? "生成中…"
                    : "继续对话,如:把按钮改成红色 / 加个重置功能"
                  : "生成完成后可继续对话迭代…"
              }
              className="flex-1 px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-40"
            />
            <button
              onClick={sendChat}
              disabled={running || !chatInput.trim() || !sessionId}
              className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40"
            >
              发送
            </button>
          </div>
        </div>
        <div className="flex flex-col overflow-hidden bg-gray-50">
          <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase border-b">
            {files.length > 0 && !previewHtml ? "生成文件" : "实时预览"}
          </div>
          <div className="flex-1 overflow-auto">
            {files.length > 0 && !previewHtml ? (
              <div className="p-3 text-sm">
                <div className="text-gray-500 mb-2">
                  多文件项目已生成到工作区(data/projects/&lt;id&gt;/workspace/):
                </div>
                <ul className="font-mono space-y-1">
                  {files.map((f) => (
                    <li key={f} className="text-gray-800">
                      📄 {f}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <PreviewFrame html={previewHtml} />
            )}
          </div>
          <div className="h-2/5 border-t flex flex-col">
            <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase border-b">
              工件
            </div>
            <div className="flex-1 bg-white">
              <ArtifactPanel artifacts={artifacts} />
            </div>
          </div>
        </div>
        <div className="overflow-y-auto bg-white p-3">
          <AgentTeam
            agents={agents}
            current={currentAgent}
            completed={completed}
          />
        </div>
      </div>
    </div>
  );
}

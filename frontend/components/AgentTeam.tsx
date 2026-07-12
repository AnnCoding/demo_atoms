import type { AgentInfo } from "@/lib/types";

export default function AgentTeam({
  agents,
  current,
  completed,
}: {
  agents: AgentInfo[];
  current: string[];
  completed: string[];
}) {
  return (
    <div className="space-y-1.5">
      <div className="text-xs font-semibold text-gray-400 uppercase mb-1">
        AI 团队
      </div>
      {agents.map((a) => {
        const status = current.includes(a.name)
          ? "working"
          : completed.includes(a.name)
            ? "done"
            : "idle";
        return (
          <div
            key={a.id}
            className={
              "flex items-center gap-2 px-2 py-1.5 rounded text-sm " +
              (status === "working"
                ? "bg-blue-50 border border-blue-300"
                : status === "done"
                  ? "opacity-60"
                  : "")
            }
          >
            <span className="text-lg">{a.emoji}</span>
            <div className="flex-1">
              <div className="font-medium">{a.name}</div>
              <div className="text-xs text-gray-500">{a.role}</div>
            </div>
            {status === "working" && (
              <span className="text-xs text-blue-500 animate-pulse">
                {current.length > 1 ? "并行工作中…" : "工作中…"}
              </span>
            )}
            {status === "done" && (
              <span className="text-xs text-green-500">✓</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

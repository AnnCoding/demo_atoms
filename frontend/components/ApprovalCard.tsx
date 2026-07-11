import type { Approval } from "@/lib/types";

export default function ApprovalCard({
  approval,
  onApprove,
}: {
  approval: Approval | null;
  onApprove: () => void;
}) {
  if (!approval) return null;
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
        <div className="px-5 py-3 border-b font-semibold">
          🤝 审批确认 — {approval.artifact}
        </div>
        <pre className="flex-1 overflow-auto p-4 text-xs whitespace-pre-wrap text-gray-700">
          {(approval.value || "").slice(0, 4000)}
        </pre>
        <div className="px-5 py-3 border-t flex justify-end gap-2">
          <button className="px-4 py-1.5 text-sm rounded-lg border border-gray-300 text-gray-500">
            修改
          </button>
          <button
            onClick={onApprove}
            className="px-4 py-1.5 text-sm rounded-lg bg-green-600 text-white hover:bg-green-700"
          >
            ✓ 确认,继续
          </button>
        </div>
      </div>
    </div>
  );
}

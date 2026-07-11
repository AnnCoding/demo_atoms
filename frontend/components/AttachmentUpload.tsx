"use client";

type Att = { id: string; filename: string; kind: string };

export default function AttachmentUpload({
  attachments,
  onUpload,
  onRemove,
}: {
  attachments: Att[];
  onUpload: (f: File) => void;
  onRemove: (id: string) => void;
}) {
  return (
    <div>
      <label className="inline-block px-3 py-1.5 text-sm rounded-lg border border-dashed border-gray-400 cursor-pointer hover:border-blue-400">
        + 添加附件
        <input
          type="file"
          className="hidden"
          multiple
          onChange={(e) => {
            const fs = e.target.files;
            if (fs) Array.from(fs).forEach(onUpload);
            e.target.value = "";
          }}
        />
      </label>
      <div className="flex flex-wrap gap-1 mt-2">
        {attachments.map((a) => (
          <span
            key={a.id}
            className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded bg-gray-100"
          >
            📎 {a.filename}
            <button
              onClick={() => onRemove(a.id)}
              className="text-gray-400 hover:text-red-500"
            >
              ×
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}

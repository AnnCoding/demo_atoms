"use client";
import type { ModeInfo } from "@/lib/types";

export default function ModeSwitch({
  modes,
  value,
  onChange,
}: {
  modes: ModeInfo[];
  value: string;
  onChange: (m: string) => void;
}) {
  return (
    <div className="flex gap-2 flex-wrap">
      {modes.map((m) => (
        <button
          key={m.id}
          title={m.desc}
          onClick={() => onChange(m.id)}
          className={
            "px-3 py-2 rounded-lg border text-sm " +
            (value === m.id
              ? "bg-blue-600 text-white border-blue-600"
              : "bg-white border-gray-300 hover:border-blue-400")
          }
        >
          <span className="mr-1">{m.emoji}</span>
          {m.name}
        </button>
      ))}
    </div>
  );
}

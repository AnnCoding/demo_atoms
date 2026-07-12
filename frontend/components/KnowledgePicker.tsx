"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getJSON } from "@/lib/api";

type Item = { id: string; title: string; tags: string[]; remembered: boolean };

export default function KnowledgePicker({
  value,
  onChange,
}: {
  value: string[];
  onChange: (ids: string[]) => void;
}) {
  const [items, setItems] = useState<Item[]>([]);
  useEffect(() => {
    getJSON<{ items: Item[] }>("/api/knowledge")
      .then((result) => setItems(result.items || []))
      .catch(() => setItems([]));
  }, []);
  if (!items.length) {
    return (
      <div className="text-xs text-gray-400">
        暂无知识内容，可前往{" "}
        <Link href="/knowledge" className="text-blue-600">
          知识库
        </Link>{" "}
        上传。
      </div>
    );
  }
  return (
    <div className="flex max-h-28 flex-wrap gap-2 overflow-y-auto">
      {items.map((item) => {
        const selected = value.includes(item.id);
        return (
          <button
            type="button"
            key={item.id}
            onClick={() =>
              onChange(
                selected
                  ? value.filter((id) => id !== item.id)
                  : [...value, item.id],
              )
            }
            className={`rounded-lg border px-3 py-2 text-left text-xs ${selected ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-200 text-gray-600"}`}
          >
            {selected ? "✓ " : "📄 "}
            {item.title}
            {item.remembered && (
              <span className="ml-1 text-[10px] text-violet-500">已记忆</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

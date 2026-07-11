"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { API } from "@/lib/api";

type Project = {
  id: string;
  idea: string;
  mode: string;
  share_slug: string;
  created_at: number;
};

export default function Projects() {
  const [items, setItems] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/projects`)
      .then((r) => r.json())
      .then((j) => setItems(j.projects || []))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-1">🌐 公开作品库</h1>
      <p className="text-gray-500 mb-6">所有生成过的应用,点击打开即用。</p>

      {loading && <div className="text-gray-400">加载中…</div>}
      {items.length === 0 && !loading && (
        <div className="text-gray-400 border border-dashed rounded-lg p-12 text-center">
          还没有作品,去{" "}
          <Link href="/" className="text-blue-600">
            生成一个
          </Link>{" "}
          吧
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {items.map((p) => (
          <Link
            key={p.id}
            href={`/p/${p.share_slug}`}
            className="block border rounded-lg overflow-hidden hover:border-blue-400 hover:shadow-md transition bg-white"
          >
            <div className="relative h-32 bg-gray-100 overflow-hidden border-b">
              <iframe
                src={`${API}/api/apps/${p.share_slug}.html`}
                className="absolute top-0 left-0 origin-top-left pointer-events-none"
                style={{
                  width: "440px",
                  height: "195px",
                  transform: "scale(0.66)",
                }}
                sandbox="allow-scripts"
                loading="lazy"
                title={p.idea}
              />
            </div>
            <div className="p-4">
              <div className="text-xs text-gray-400 mb-1">
                {p.mode === "engineer"
                  ? "⚙️ 工程师"
                  : p.mode === "team"
                    ? "👥 团队"
                    : "🔬 深度研究"}
                {" · "}
                {new Date((p.created_at || 0) * 1000).toLocaleString("zh-CN")}
              </div>
              <div className="text-sm font-medium line-clamp-2">{p.idea}</div>
              <div className="mt-2 text-xs text-blue-600">打开应用 ↗</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

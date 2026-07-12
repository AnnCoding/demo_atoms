"use client";

import { useEffect, useState } from "react";
import { getJSON, sendJSON, uploadForm } from "@/lib/api";

type Knowledge = {
  id: string;
  title: string;
  description: string;
  tags: string[];
  filename: string;
  kind: string;
  excerpt: string;
  remembered: boolean;
  published: boolean;
  owner_id: string;
  updated_at: number;
};

export default function KnowledgePage() {
  const [tab, setTab] = useState<"mine" | "square">("mine");
  const [mine, setMine] = useState<Knowledge[]>([]);
  const [square, setSquare] = useState<Knowledge[]>([]);
  const [query, setQuery] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [publish, setPublish] = useState(false);
  const [message, setMessage] = useState("");

  const loadMine = () =>
    getJSON<{ items: Knowledge[] }>("/api/knowledge").then((data) =>
      setMine(data.items || []),
    );
  const loadSquare = () =>
    getJSON<{ items: Knowledge[] }>(
      `/api/knowledge/square?q=${encodeURIComponent(query)}`,
    ).then((data) => setSquare(data.items || []));
  useEffect(() => {
    loadMine();
    loadSquare();
  }, []);

  const upload = async () => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    form.append("title", title);
    form.append("description", description);
    form.append("tags", tags);
    form.append("remember", "true");
    form.append("publish", String(publish));
    setMessage("正在提取内容并写入长期记忆…");
    try {
      await uploadForm("/api/knowledge/upload", form);
      setMessage(
        publish ? "已上传、记忆并发布到知识广场" : "已上传并加入私有长期记忆",
      );
      setFile(null);
      setTitle("");
      setDescription("");
      setTags("");
      setPublish(false);
      loadMine();
      loadSquare();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "上传失败");
    }
  };

  const update = async (item: Knowledge, body: Record<string, unknown>) => {
    await sendJSON(`/api/knowledge/${item.id}`, "PATCH", body);
    loadMine();
    loadSquare();
  };

  const remove = async (item: Knowledge) => {
    if (!window.confirm(`删除知识「${item.title}」？`)) return;
    await sendJSON(`/api/knowledge/${item.id}`, "DELETE");
    loadMine();
    loadSquare();
  };

  const cards = tab === "mine" ? mine : square;
  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-bold">📚 知识库与知识广场</h1>
      <p className="mt-1 text-sm text-gray-500">
        上传内容默认进入私有长期记忆；只有你明确开启发布时，才会出现在公共广场。
      </p>

      <div className="mt-6 rounded-xl border bg-white p-5 shadow-sm">
        <h2 className="font-semibold">上传到我的知识库</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="知识标题（默认使用文件名）"
            className="rounded-lg border px-3 py-2 text-sm"
          />
          <input
            value={tags}
            onChange={(event) => setTags(event.target.value)}
            placeholder="标签，用逗号分隔"
            className="rounded-lg border px-3 py-2 text-sm"
          />
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="介绍这份知识适合解决什么问题"
            className="rounded-lg border px-3 py-2 text-sm md:col-span-2"
          />
          <input
            type="file"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            className="text-sm"
          />
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={publish}
              onChange={(event) => setPublish(event.target.checked)}
            />
            同时发布到知识广场（公开分享）
          </label>
        </div>
        <button
          onClick={upload}
          disabled={!file}
          className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-40"
        >
          上传并记忆
        </button>
        {message && (
          <span className="ml-3 text-sm text-blue-600">{message}</span>
        )}
      </div>

      <div className="mt-8 flex items-center gap-2 border-b">
        <button
          onClick={() => setTab("mine")}
          className={`px-4 py-2 text-sm ${tab === "mine" ? "border-b-2 border-blue-600 text-blue-600" : "text-gray-500"}`}
        >
          我的知识库 ({mine.length})
        </button>
        <button
          onClick={() => setTab("square")}
          className={`px-4 py-2 text-sm ${tab === "square" ? "border-b-2 border-blue-600 text-blue-600" : "text-gray-500"}`}
        >
          知识广场 ({square.length})
        </button>
        {tab === "square" && (
          <div className="ml-auto flex gap-2 pb-2">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="搜索公开知识"
              className="rounded-lg border px-3 py-1.5 text-sm"
            />
            <button
              onClick={loadSquare}
              className="rounded-lg border px-3 py-1.5 text-sm"
            >
              搜索
            </button>
          </div>
        )}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {cards.map((item) => (
          <article
            key={item.id}
            className="rounded-xl border bg-white p-4 shadow-sm"
          >
            <div className="flex items-start gap-2">
              <div className="flex-1 font-semibold">{item.title}</div>
              {item.published && (
                <span className="rounded-full bg-violet-100 px-2 py-1 text-[10px] text-violet-700">
                  公开
                </span>
              )}
            </div>
            <div className="mt-1 text-xs text-gray-400">
              {item.filename} · {item.kind}
            </div>
            <p className="mt-3 line-clamp-4 text-sm leading-relaxed text-gray-600">
              {item.description || item.excerpt || "暂无文本摘要"}
            </p>
            <div className="mt-3 flex flex-wrap gap-1">
              {(item.tags || []).map((tag) => (
                <span
                  key={tag}
                  className="rounded bg-gray-100 px-2 py-1 text-[10px] text-gray-600"
                >
                  #{tag}
                </span>
              ))}
            </div>
            {tab === "mine" && (
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  onClick={() => update(item, { remembered: !item.remembered })}
                  className="rounded-lg border px-3 py-1.5 text-xs"
                >
                  {item.remembered ? "移出记忆" : "加入记忆"}
                </button>
                <button
                  onClick={() => update(item, { published: !item.published })}
                  className="rounded-lg border px-3 py-1.5 text-xs"
                >
                  {item.published ? "取消发布" : "发布到广场"}
                </button>
                <button
                  onClick={() => remove(item)}
                  className="rounded-lg border px-3 py-1.5 text-xs text-red-600"
                >
                  删除
                </button>
              </div>
            )}
            {tab === "square" && (
              <div className="mt-4 text-xs text-gray-400">
                分享者：{item.owner_id || "匿名用户"}
              </div>
            )}
          </article>
        ))}
        {cards.length === 0 && (
          <div className="col-span-full rounded-xl border border-dashed p-10 text-center text-sm text-gray-400">
            暂无知识内容
          </div>
        )}
      </div>
    </div>
  );
}

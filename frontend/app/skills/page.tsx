"use client";

import { useEffect, useState } from "react";
import { getJSON, sendJSON, uploadForm } from "@/lib/api";

type Skill = {
  name?: string;
  id?: string;
  display_name?: string;
  description: string;
  category: string;
  target_agent?: string;
  target?: string;
  source: "builtin" | "user";
  enabled?: boolean;
  invalid?: boolean;
  error?: string;
};

export default function SkillsPage() {
  const [builtin, setBuiltin] = useState<Skill[]>([]);
  const [installed, setInstalled] = useState<Skill[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () =>
    getJSON<{ builtin: Skill[]; installed: Skill[] }>("/api/user-skills")
      .then((data) => {
        setBuiltin(data.builtin || []);
        setInstalled(data.installed || []);
      })
      .catch((error) => setMessage(error.message));

  useEffect(() => {
    void load();
  }, []);

  const install = async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    setBusy(true);
    setMessage("正在执行安装链路：解析 → 校验 → 持久化 → 激活…");
    try {
      const result = await uploadForm<{
        skill: Skill;
        pipeline: { name: string }[];
      }>("/api/user-skills/install", form);
      setMessage(
        `安装完成：${result.pipeline.map((stage) => stage.name).join(" → ")}`,
      );
      load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "安装失败");
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (skill: Skill) => {
    await sendJSON(`/api/user-skills/${skill.name}`, "PATCH", {
      enabled: !skill.enabled,
    });
    load();
  };

  const remove = async (skill: Skill) => {
    if (
      !window.confirm(
        `卸载 ${skill.display_name || skill.name}？内置 Skill 不受影响。`,
      )
    )
      return;
    await sendJSON(`/api/user-skills/${skill.name}`, "DELETE");
    load();
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="flex flex-wrap items-start gap-4">
        <div>
          <h1 className="text-2xl font-bold">🧩 Skill 管理</h1>
          <p className="mt-1 text-sm text-gray-500">
            内置 Skill 始终保留；用户 Skill 经过安全校验后动态加入路由和 Agent
            Prompt。
          </p>
        </div>
        <label className="ml-auto cursor-pointer rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          {busy ? "安装中…" : "+ 安装 YAML / JSON Skill"}
          <input
            type="file"
            accept=".yaml,.yml,.json,application/json,text/yaml"
            disabled={busy}
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) install(file);
              event.target.value = "";
            }}
          />
        </label>
      </div>
      {message && (
        <div className="mt-4 rounded-lg bg-blue-50 p-3 text-sm text-blue-700">
          {message}
        </div>
      )}

      <section className="mt-8">
        <h2 className="mb-3 font-semibold">
          我安装的 Skill ({installed.length})
        </h2>
        {installed.length === 0 ? (
          <div className="rounded-xl border border-dashed p-8 text-center text-sm text-gray-400">
            尚未安装自定义 Skill。可从模板开始：GET /api/user-skills/template
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {installed.map((skill) => (
              <div
                key={skill.name}
                className="rounded-xl border bg-white p-4 shadow-sm"
              >
                <div className="flex items-start gap-2">
                  <div className="flex-1">
                    <div className="font-semibold">
                      {skill.display_name || skill.name}
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      {skill.category} · {skill.target_agent}
                    </div>
                  </div>
                  <span
                    className={`rounded-full px-2 py-1 text-[10px] ${skill.enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}
                  >
                    {skill.enabled ? "已启用" : "已停用"}
                  </span>
                </div>
                <p className="mt-3 min-h-10 text-sm text-gray-600">
                  {skill.invalid ? skill.error : skill.description}
                </p>
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={() => toggle(skill)}
                    className="rounded-lg border px-3 py-1.5 text-xs hover:border-blue-400"
                  >
                    {skill.enabled ? "停用" : "启用"}
                  </button>
                  <button
                    onClick={() => remove(skill)}
                    className="rounded-lg border px-3 py-1.5 text-xs text-red-600 hover:border-red-300"
                  >
                    卸载
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="mt-10">
        <h2 className="mb-3 font-semibold">
          系统内置 Skill ({builtin.length})
        </h2>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {builtin.map((skill) => (
            <div
              key={skill.id || skill.name}
              className="rounded-xl border bg-gray-50 p-4"
            >
              <div className="flex items-center gap-2">
                <div className="font-medium">
                  {skill.display_name || skill.id}
                </div>
                <span className="rounded bg-gray-200 px-2 py-0.5 text-[10px] text-gray-600">
                  只读内置
                </span>
              </div>
              <p className="mt-2 text-sm text-gray-600">{skill.description}</p>
              <div className="mt-2 text-xs text-gray-400">
                {skill.category} · {skill.target}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

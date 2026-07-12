"""每项目长期记忆:在 data/projects/{id}/ 下维护架构/进度/决策文档。

  data/projects/{id}/
    architecture.md   架构文档(来自 Bob;simple 模式可缺)
    progress.md       进度日志(各步完成记录)
    decisions.md      决策记忆(分流结论、用户澄清、验收结论)
    app.html          生成的应用(可直接打开)
    project.json      元数据
    memory.json       给 Agent 注入的结构化长期记忆
"""
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "..", "data")  # demo_show/data
PROJECTS_DIR = os.path.join(DATA_DIR, "projects")


class ProjectMemory:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.dir = os.path.join(PROJECTS_DIR, project_id)
        os.makedirs(self.dir, exist_ok=True)
        self.arch_path = os.path.join(self.dir, "architecture.md")
        self.progress_path = os.path.join(self.dir, "progress.md")
        self.decisions_path = os.path.join(self.dir, "decisions.md")
        self.code_path = os.path.join(self.dir, "app.html")
        self.meta_path = os.path.join(self.dir, "project.json")
        self.memory_path = os.path.join(self.dir, "memory.json")

    def _append(self, path: str, msg: str):
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"- [{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

    def append_progress(self, msg: str):
        self._append(self.progress_path, msg)

    def add_decision(self, msg: str):
        self._append(self.decisions_path, msg)

    def write_arch(self, text: str):
        if text:
            with open(self.arch_path, "w", encoding="utf-8") as f:
                f.write(text)

    def write_code(self, html: str):
        if html:
            with open(self.code_path, "w", encoding="utf-8") as f:
                f.write(html)

    def save_meta(self, meta: dict):
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def load_snapshot(self) -> dict:
        try:
            with open(self.memory_path, encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def remember_message(self, role: str, content: str, agent: str = "") -> dict:
        """Persist compact conversational memory independent of process/Redis life."""
        memory = self.load_snapshot()
        messages = memory.setdefault("recent_messages", [])
        messages.append({"role": role, "agent": agent, "content": content, "at": time.time()})
        memory["recent_messages"] = messages[-16:]
        self._save_snapshot(memory)
        return memory

    def remember_fact(self, category: str, value) -> dict:
        memory = self.load_snapshot()
        bucket = memory.setdefault(category, [])
        if value not in bucket:
            bucket.append(value)
        memory[category] = bucket[-30:]
        self._save_snapshot(memory)
        return memory

    def _save_snapshot(self, memory: dict):
        tmp = self.memory_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.memory_path)

    def prompt_context(self, conversation: list | None = None) -> str:
        """Bounded, structured prompt context. Full history remains persisted."""
        memory = self.load_snapshot()
        if conversation:
            normalized = []
            for item in conversation[-12:]:
                if not isinstance(item, dict):
                    continue
                normalized.append({
                    "role": item.get("role", ""),
                    "agent": item.get("agent", ""),
                    "content": item.get("content") or item.get("text") or "",
                })
            memory["recent_messages"] = normalized
        return json.dumps(memory, ensure_ascii=False, indent=2)[:12000]

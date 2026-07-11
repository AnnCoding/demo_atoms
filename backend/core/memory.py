"""每项目长期记忆:在 data/projects/{id}/ 下维护架构/进度/决策文档。

  data/projects/{id}/
    architecture.md   架构文档(来自 Bob;simple 模式可缺)
    progress.md       进度日志(各步完成记录)
    decisions.md      决策记忆(分流结论、用户澄清、验收结论)
    app.html          生成的应用(可直接打开)
    project.json      元数据
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

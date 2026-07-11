"""文件工具:agent 在「每项目工作区」内读写文件。

工作区 = data/projects/{project_id}/workspace/
路径强制限制在工作区内(防越权)。orchestrator 在每会话开始时 set_workspace(project_id)。
"""
import os

from connectors.base import Connector

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "..", "data")

_workspace = None


def set_workspace(project_id: str):
    global _workspace
    _workspace = os.path.normpath(os.path.join(DATA_DIR, "projects", project_id, "workspace"))
    os.makedirs(_workspace, exist_ok=True)


def get_workspace():
    return _workspace


def _safe_path(rel: str) -> str:
    ws = get_workspace()
    if not ws:
        raise RuntimeError("工作区未设置(无法使用文件工具)")
    rel = (rel or "").lstrip("/\\")
    full = os.path.normpath(os.path.join(ws, rel))
    if not (full == ws or full.startswith(ws + os.sep)):
        raise ValueError("非法路径:越出工作区")
    return full


class FileWriteTool(Connector):
    id = "file_write"
    schema = {
        "name": "file_write",
        "description": "把内容写入工作区文件(相对路径,如 src/main.py)。已存在则覆盖。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对路径"},
                "content": {"type": "string", "description": "文件完整内容"},
            },
            "required": ["path", "content"],
        },
    }

    async def call(self, path: str, content: str) -> str:
        full = _safe_path(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return f"已写入 {path}({len(content)} 字符)"


class FileReadTool(Connector):
    id = "file_read"
    schema = {
        "name": "file_read",
        "description": "读取工作区内某文件内容(最多 4000 字符)。",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "相对路径"}},
            "required": ["path"],
        },
    }

    async def call(self, path: str) -> str:
        full = _safe_path(path)
        if not os.path.exists(full):
            return f"[{path} 不存在]"
        if os.path.isdir(full):
            # 传了目录:列出条目,引导读取具体文件(避免 IsADirectoryError)
            entries = sorted(os.listdir(full))
            items = []
            for e in entries:
                tag = "/" if os.path.isdir(os.path.join(full, e)) else ""
                items.append(f"  {e}{tag}")
            hint = f"[{path} 是目录,共 {len(entries)} 个条目]\n" + "\n".join(items)
            hint += "\n请用具体文件路径(如 index.html、package.json)再调用 file_read。"
            return hint
        with open(full, encoding="utf-8") as f:
            return f.read()[:4000]


class FileEditTool(Connector):
    id = "file_edit"
    schema = {
        "name": "file_edit",
        "description": "对工作区内文件做一次字符串替换(old → new)。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
        },
    }

    async def call(self, path: str, old: str, new: str) -> str:
        full = _safe_path(path)
        if not os.path.exists(full):
            return f"[{path} 不存在]"
        if os.path.isdir(full):
            return f"[{path} 是目录,无法编辑,请指定具体文件]"
        with open(full, encoding="utf-8") as f:
            txt = f.read()
        if old not in txt:
            return f"[{path} 未找到匹配文本]"
        with open(full, "w", encoding="utf-8") as f:
            f.write(txt.replace(old, new, 1))
        return f"已编辑 {path}"


def list_workspace_files() -> list:
    ws = get_workspace()
    if not ws or not os.path.isdir(ws):
        return []
    out = []
    for root, _dirs, files in os.walk(ws):
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, ws).replace(os.sep, "/")
            out.append({"path": rel, "size": os.path.getsize(full)})
    return sorted(out, key=lambda x: x["path"])


def read_workspace_file(rel_path: str) -> str:
    """读取工作区内指定文件内容，不存在则返回空字符串。"""
    ws = get_workspace()
    if not ws:
        return ""
    full = os.path.normpath(os.path.join(ws, rel_path.lstrip("/\\")))
    if not (full == ws or full.startswith(ws + os.sep)):
        return ""
    if not os.path.isfile(full):
        return ""
    try:
        with open(full, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

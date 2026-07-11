"""持久化。v1 本地文件;配置 Supabase 后切换为 Postgres + Storage。

数据落在本项目 data/ 目录,方便排查:
  data/projects.json     所有项目(主数据)
  data/apps/{slug}.html  每个生成应用的可直接打开 HTML(双击即看)
  data/uploads/           附件原件
"""
import json
import os
import secrets
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))          # backend/core
DATA_DIR = os.path.join(HERE, "..", "..", "data")          # demo_show/data
APPS_DIR = os.path.join(DATA_DIR, "apps")
os.makedirs(APPS_DIR, exist_ok=True)

LOCAL_DB = os.getenv("LOCAL_DB", os.path.join(DATA_DIR, "projects.json"))


def _load() -> list:
    if os.path.exists(LOCAL_DB):
        with open(LOCAL_DB, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save(rows: list):
    with open(LOCAL_DB, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def _dump_app(row: dict):
    """把生成应用单独存一份 .html,方便直接打开排查。"""
    code = row.get("code") or ""
    if code:
        slug = row.get("share_slug") or row.get("id")
        os.makedirs(APPS_DIR, exist_ok=True)  # 防御:目录可能被外部清理,写前确保存在
        with open(os.path.join(APPS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(code)


def save_project(session) -> dict:
    """按 project_id upsert:首次新建,迭代时更新同一行(保留 share_slug/created_at)。

    存 spec/arch/code/report + files(多文件项目文件树)。
    """
    pid = getattr(session, "project_id", None) or str(uuid.uuid4())
    rows = _load()
    row = next((r for r in rows if r.get("id") == pid), None)
    if row is None:
        # 首次创建
        row = {
            "id": pid,
            "idea": session.idea,
            "mode": session.mode,
            "status": "published",
            "share_slug": secrets.token_urlsafe(6),
            "created_at": int(time.time()),
        }
        rows.append(row)
    # 产物字段:首次与迭代都覆盖
    row["spec"] = session.artifacts.get("spec")
    row["arch"] = session.artifacts.get("arch")
    row["code"] = session.artifacts.get("code")
    row["report"] = session.artifacts.get("report")
    row["files"] = session.artifacts.get("files") or []
    row["conversation"] = getattr(session, "conversation", []) or []
    row["output_format"] = getattr(session, "output_format", "single_html") or "single_html"
    row["updated_at"] = int(time.time())
    _save(rows)
    _dump_app(row)
    return row


def _rebuild_conversation(row: dict) -> list:
    """旧作品没有 conversation 时,从 artifacts 重建简化对话(best-effort,供作品页展示)。"""
    conv = []
    if row.get("idea"):
        conv.append({"role": "user", "agent": "", "text": row["idea"]})
    spec = row.get("spec") or ""
    if spec:
        name = ""
        try:
            d = json.loads(spec)
            name = d.get("product_name", "") if isinstance(d, dict) else ""
        except Exception:
            pass
        conv.append({"role": "assistant", "agent": "Emma",
                     "text": "需求规格已完成" + (f": {name}" if name else "")})
    if row.get("arch"):
        conv.append({"role": "assistant", "agent": "Bob",
                     "text": "技术架构已完成: " + (row["arch"] or "").strip()[:100]})
    if row.get("report"):
        conv.append({"role": "assistant", "agent": "Iris",
                     "text": "调研报告已完成: " + (row["report"] or "").strip()[:100]})
    if row.get("code"):
        conv.append({"role": "assistant", "agent": "Alex",
                     "text": "代码实现已完成"})
    return conv


def get_project(slug: str):
    for r in _load():
        if r.get("share_slug") == slug:
            # 旧作品没有 conversation:从 artifacts 重建简化对话
            if not r.get("conversation"):
                r["conversation"] = _rebuild_conversation(r)
            return r
    return None


def list_projects(limit: int = 50):
    rows = [r for r in _load() if r.get("status") == "published"]
    rows.sort(key=lambda r: r.get("created_at", 0), reverse=True)
    return rows[:limit]

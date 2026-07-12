"""会话状态(短期记忆)。STM 后备:REDIS_URL 配置走 Redis,否则内存。

多轮迭代支持:history(对话历史)/iteration(迭代轮次)/last_user_msg(最新修改指令)。
"""
import dataclasses
import uuid
from dataclasses import dataclass, field
from typing import Dict, List

from .shortterm import ShortTermMemory

_stm = ShortTermMemory()


@dataclass
class Session:
    id: str
    mode: str
    idea: str
    attachment_ids: List[str] = field(default_factory=list)
    artifacts: Dict[str, object] = field(default_factory=dict)
    idx: int = 0
    project_id: str = ""
    steps: list = field(default_factory=list)
    clarify_round: int = 0
    clarify_answers: str = ""
    skills: List[str] = field(default_factory=list)   # 命中的 skill id
    # ---- 多轮迭代 ----
    history: list = field(default_factory=list)        # [{role:"user"|"assistant", content:"..."}]
    iteration: int = 0                                  # 已完成迭代轮数(0=初始生成)
    last_user_msg: str = ""                             # 最新一条用户修改指令
    # ---- 持久化对话历史(落 projects.json,供作品页展示)----
    # [{role:"user"|"assistant", agent:"...", text:"..."}]
    conversation: list = field(default_factory=list)
    # ---- 产物形态(markdown / single_html / webpage / multi_file)----
    output_format: str = "single_html"
    # ---- v2 orchestration / event protocol ----
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_seq: int = 0
    completed_outputs: List[str] = field(default_factory=list)
    intent: Dict[str, object] = field(default_factory=dict)
    memory_snapshot: Dict[str, object] = field(default_factory=dict)
    owner_id: str = "local-user"
    knowledge_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Session":
        from modes.registry import Step
        d = dict(d)
        # 向后兼容:旧 session 序列化时没有迭代字段,补默认值
        d.setdefault("history", [])
        d.setdefault("iteration", 0)
        d.setdefault("last_user_msg", "")
        d.setdefault("conversation", [])
        d.setdefault("output_format", "single_html")
        d.setdefault("run_id", uuid.uuid4().hex)
        d.setdefault("event_seq", 0)
        d.setdefault("completed_outputs", [])
        d.setdefault("intent", {})
        d.setdefault("memory_snapshot", {})
        d.setdefault("owner_id", "local-user")
        d.setdefault("knowledge_ids", [])
        steps = []
        for s in d.get("steps", []):
            steps.append(s if isinstance(s, Step) else Step(**s))
        d["steps"] = steps
        return cls(**d)


def new_session(mode: str, idea: str, attachment_ids: list = None, skill_id: str = None,
                owner_id: str = "local-user", knowledge_ids: list = None) -> Session:
    from modes.registry import PIPELINES
    s = Session(
        id=uuid.uuid4().hex,
        mode=mode,
        idea=idea,
        attachment_ids=attachment_ids or [],
        project_id=str(uuid.uuid4()),
        steps=list(PIPELINES.get(mode, [])),
        skills=[skill_id] if skill_id else [],
        owner_id=owner_id or "local-user",
        knowledge_ids=knowledge_ids or [],
    )
    _stm.set("session:" + s.id, s.to_dict())
    return s


def session_from_project(row: dict) -> "Session":
    """从作品(projects.json 一行)重建 session,支持基于作品的继续对话。

    复用作品的 project_id,使 save_project upsert 同一作品(更新 code/conversation),
    从而实现「历史对话与作品持久绑定 + 随时可继续对话」。
    """
    from modes.registry import PIPELINES
    conversation = row.get("conversation") or []
    user_msgs = [
        m for m in conversation
        if isinstance(m, dict) and m.get("role") == "user"
    ]
    s = Session(
        id=uuid.uuid4().hex,
        mode=row.get("mode") or "engineer",
        idea=row.get("idea") or "",
        project_id=row.get("id") or str(uuid.uuid4()),
        artifacts={
            "code": row.get("code") or "",
            "spec": row.get("spec"),
            "arch": row.get("arch"),
            "report": row.get("report"),
            "files": row.get("files") or [],
        },
        steps=list(PIPELINES.get(row.get("mode") or "engineer", [])),
        conversation=conversation,
        iteration=max(0, len(user_msgs) - 1),  # 第一条 user 是初始 idea
        output_format=row.get("output_format") or "single_html",
    )
    s.idx = len(s.steps)  # 标记 pipeline 已完成 → 满足迭代入口条件
    _stm.set("session:" + s.id, s.to_dict())
    return s


def get_session(sid: str):
    d = _stm.get("session:" + sid)
    return Session.from_dict(d) if d else None


def save_session(s: Session):
    _stm.set("session:" + s.id, s.to_dict())

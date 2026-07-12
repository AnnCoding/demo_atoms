"""Skill 管理核心：Skill 数据类 + SkillManager。

参考 daily_stock_analysis 架构：
- Skill 定义在 strategies/*.yaml 中
- SkillManager 加载、注册、激活 skill
- Skill instructions 注入到 agent 的 system prompt
"""
import os
import copy
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import yaml
import logging

log = logging.getLogger("atoms.skills")

# 内置 strategies 目录
_BUILTIN_STRATEGIES_DIR = Path(__file__).parent.parent.parent / "strategies"
_DEFAULT_USER_SKILLS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "user_skills"


@dataclass
class Skill:
    """Skill 定义。

    YAML 格式：
        name: react-app
        display_name: React / Next.js 前端应用
        description: 生成多文件 Next.js 项目
        category: frontend
        trigger_keywords: [react, next.js, dashboard]
        target_agent: alex
        collaborator_agents: []
        required_tools: [file_write, file_read]
        default_active: false
        default_router: true
        default_priority: 10
        instructions: |
          详细指导文本...
    """
    name: str
    display_name: str
    description: str
    instructions: str
    category: str = "general"
    trigger_keywords: List[str] = field(default_factory=list)
    target_agent: str = "alex"
    collaborator_agents: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    default_active: bool = False
    default_router: bool = False
    default_priority: int = 100
    enabled: bool = True  # 运行时状态
    source: str = "builtin"  # builtin | user

    def to_dict(self) -> dict:
        """序列化为字典（用于前端展示）。"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "trigger_keywords": self.trigger_keywords,
            "target_agent": self.target_agent,
            "collaborator_agents": self.collaborator_agents,
            "required_tools": self.required_tools,
            "default_active": self.default_active,
            "default_router": self.default_router,
            "default_priority": self.default_priority,
            "enabled": self.enabled,
            "source": self.source,
        }


def _coerce_bool(val, default=False) -> bool:
    """强制转换为 bool。"""
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "yes", "1")
    return bool(val)


def _coerce_int(val, default=100) -> int:
    """强制转换为 int。"""
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _coerce_list(val) -> List[str]:
    """强制转换为字符串列表。"""
    if not val:
        return []
    if isinstance(val, str):
        return [val]
    return [str(x).strip() for x in val if str(x).strip()]


def load_skill_from_yaml(filepath) -> Skill:
    """从 YAML 文件加载 Skill。

    Args:
        filepath: YAML 文件路径（str 或 Path）

    Returns:
        Skill 对象
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Skill file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    name = str(data.get("name") or filepath.stem).strip()
    if not name:
        raise ValueError(f"Skill name missing in {filepath}")

    return Skill(
        name=name,
        display_name=str(data.get("display_name") or name).strip(),
        description=str(data.get("description") or "").strip(),
        instructions=str(data.get("instructions") or "").strip(),
        category=str(data.get("category") or "general").strip(),
        trigger_keywords=_coerce_list(data.get("trigger_keywords")),
        target_agent=str(data.get("target_agent") or "alex").strip(),
        collaborator_agents=_coerce_list(data.get("collaborator_agents")),
        required_tools=_coerce_list(data.get("required_tools")),
        default_active=_coerce_bool(data.get("default_active"), False),
        default_router=_coerce_bool(data.get("default_router"), False),
        default_priority=_coerce_int(data.get("default_priority"), 100),
        enabled=True,
    )


def load_skills_from_directory(directory: Path) -> List[Skill]:
    """从目录加载所有 Skill（*.yaml）。

    Args:
        directory: 目录路径

    Returns:
        Skill 列表
    """
    skills = []
    directory = Path(directory)
    if not directory.exists():
        log.warning(f"Skill directory not found: {directory}")
        return skills

    for filepath in sorted(directory.glob("*.yaml")):
        try:
            skill = load_skill_from_yaml(filepath)
            skills.append(skill)
            log.debug(f"Loaded skill: {skill.name} from {filepath}")
        except Exception as e:
            log.error(f"Failed to load skill from {filepath}: {e}")

    return skills


class SkillManager:
    """Skill 管理器：加载、注册、激活、查询。

    参考 daily_stock_analysis 的 SkillManager 设计：
    - 内置 strategies 目录
    - 可选的自定义 strategies 目录
    - 模块级缓存优化（prototype + deepcopy）
    """

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._custom_dir: Optional[Path] = None

    def register(self, skill: Skill) -> None:
        """注册 Skill 到管理器。"""
        if not skill or not skill.name:
            raise ValueError("Invalid skill")
        self._skills[skill.name] = skill
        log.debug(f"Registered skill: {skill.name}")

    def load_builtin_skills(self) -> int:
        """加载内置 strategies 目录下的所有 skill。

        Returns:
            加载的 skill 数量
        """
        skills = load_skills_from_directory(_BUILTIN_STRATEGIES_DIR)
        for skill in skills:
            self.register(skill)
        log.info(f"Loaded {len(skills)} builtin skills from {_BUILTIN_STRATEGIES_DIR}")
        return len(skills)

    def load_custom_skills(self, directory) -> int:
        """加载自定义 strategies 目录下的所有 skill。

        Args:
            directory: 自定义目录路径

        Returns:
            加载的 skill 数量
        """
        if not directory:
            return 0

        directory = Path(directory)
        if not directory.exists():
            log.warning(f"Custom skill directory not found: {directory}")
            return 0

        self._custom_dir = directory
        registry = {}
        registry_path = directory / "_registry.json"
        if registry_path.exists():
            try:
                import json
                with open(registry_path, encoding="utf-8") as f:
                    registry = json.load(f) or {}
            except Exception as exc:
                log.warning("User skill registry unreadable: %s", exc)
        skills = load_skills_from_directory(directory)
        loaded = 0
        for skill in skills:
            record = registry.get(skill.name, {}) if isinstance(registry, dict) else {}
            if record and not record.get("enabled", True):
                continue
            skill.source = "user"
            self.register(skill)
            loaded += 1
        log.info(f"Loaded {loaded} enabled custom skills from {directory}")
        return loaded

    def get(self, name: str) -> Optional[Skill]:
        """获取指定名称的 Skill。"""
        return self._skills.get(name)

    def list_all_skills(self) -> List[Skill]:
        """列出所有已注册的 skill。"""
        return list(self._skills.values())

    def list_active_skills(self) -> List[Skill]:
        """列出所有激活的 skill。"""
        return [s for s in self._skills.values() if s.enabled]

    def list_default_router_skills(self) -> List[Skill]:
        """列出参与默认路由的 skill（按优先级排序）。"""
        skills = [s for s in self._skills.values() if s.default_router]
        return sorted(skills, key=lambda s: s.default_priority)

    def activate(self, skill_names: List[str]) -> None:
        """激活指定的 skill，禁用其他 skill。

        Args:
            skill_names: 要激活的 skill 名称列表
        """
        names_set = set(skill_names or [])
        for skill in self._skills.values():
            skill.enabled = skill.name in names_set
        log.info(f"Activated skills: {names_set}")

    def activate_by_default(self) -> None:
        """激活所有 default_active=True 的 skill。"""
        for skill in self._skills.values():
            skill.enabled = skill.default_active
        active_names = [s.name for s in self._skills.values() if s.enabled]
        log.info(f"Activated default skills: {active_names}")

    def match_keywords(self, text: str) -> List[str]:
        """根据关键词匹配 skill。

        Args:
            text: 用户输入文本

        Returns:
            匹配的 skill 名称列表
        """
        if not text:
            return []

        text_lower = text.lower()
        matched = []

        for skill in self._skills.values():
            for kw in skill.trigger_keywords:
                if kw.lower() in text_lower:
                    matched.append(skill.name)
                    break

        return matched

    def get_skill_instructions(self, agent_id: str = None) -> str:
        """生成激活 skill 的组合指令文本。

        参考 daily_stock_analysis 的 get_skill_instructions：
        - 按类别分组
        - 包含 skill 名称、适用场景、详细指导
        - 过滤 target_agent 或 collaborator_agents 包含当前 agent

        Args:
            agent_id: 当前 agent 的 ID（可选，用于过滤）

        Returns:
            组合的 skill instructions 文本
        """
        active = self.list_active_skills()
        if not active:
            return ""

        # 按类别分组
        grouped: Dict[str, List[Skill]] = {}
        for skill in active:
            # 过滤 agent
            if agent_id:
                if skill.target_agent != agent_id and agent_id not in skill.collaborator_agents:
                    continue

            cat = skill.category
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(skill)

        # 生成文本
        parts = []
        idx = 1
        for category in sorted(grouped.keys()):
            skills = grouped[category]
            for skill in skills:
                parts.append(
                    f"### Skill {idx}: {skill.display_name}\n"
                    f"**类别**: {skill.category}\n"
                    f"**描述**: {skill.description}\n"
                    f"**目标 Agent**: {skill.target_agent}\n"
                    f"**协作 Agent**: {', '.join(skill.collaborator_agents) or '无'}\n\n"
                    f"{skill.instructions}"
                )
                idx += 1

        return "\n\n---\n\n".join(parts)

    def catalog(self) -> List[dict]:
        """给前端 / Mike triage 的精简目录（不含 instructions）。"""
        return [
            {
                "id": s.name,
                "name": s.display_name,
                "description": s.description,
                "category": s.category,
                "target": s.target_agent,  # 前端字段名是 target
                "source": s.source,
            }
            for s in self._skills.values()
        ]


# 模块级缓存：prototype + deepcopy（参考 daily_stock_analysis）
_SKILL_MANAGER_PROTOTYPE: Optional[SkillManager] = None


def get_skill_manager(custom_dir=None) -> SkillManager:
    """获取 SkillManager 实例（带缓存）。

    首次调用从磁盘加载，后续调用返回 deepcopy 克隆。

    Args:
        custom_dir: 自定义 strategies 目录（可选）

    Returns:
        SkillManager 实例
    """
    global _SKILL_MANAGER_PROTOTYPE

    if _SKILL_MANAGER_PROTOTYPE is None:
        manager = SkillManager()
        manager.load_builtin_skills()
        _SKILL_MANAGER_PROTOTYPE = manager
        log.info("Initialized SkillManager prototype")

    # 内置 Skill 使用 prototype；用户 Skill 每次从磁盘合并，安装/启停后立即生效。
    manager = copy.deepcopy(_SKILL_MANAGER_PROTOTYPE)
    directory = Path(custom_dir) if custom_dir else _DEFAULT_USER_SKILLS_DIR
    manager.load_custom_skills(directory)
    return manager

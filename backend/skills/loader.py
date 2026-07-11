"""Skill 加载器（使用新的 SkillManager）。

重构说明：
- 保留原有的接口（兼容现有代码）
- 内部使用 agents/skills 模块的 SkillManager
- Skill 定义改为 strategies/*.yaml 格式
"""
from typing import List, Set

# 从新的 skill 模块导入
from agents.skills import get_skill_manager, route_skills


def load_all() -> list:
    """加载所有 skill（兼容接口）。

    Returns:
        skill 字典列表
    """
    manager = get_skill_manager()
    skills = manager.list_all_skills()
    return [s.to_dict() for s in skills]


def catalog() -> list:
    """给 Mike triage / 前端的精简目录（不含 instructions）。"""
    manager = get_skill_manager()
    return manager.catalog()


def get(skill_id: str):
    """获取指定 skill（兼容接口）。"""
    manager = get_skill_manager()
    skill = manager.get(skill_id)
    return skill.to_dict() if skill else None


def match(idea: str) -> list:
    """关键词匹配 idea，返回命中的 skill id 列表（兼容接口）。"""
    return route_skills(idea, mode="auto")


def match_keywords(idea: str) -> list:
    """纯关键词匹配（不走 default_router 兜底）。

    用于和 Mike 的显式选择做【并集】：确保 记账/待办/笔记 等强关键词命中的
    skill（如 local_markdown_storage）即使被 Mike 漏选，也会被补进 session.skills。
    """
    return get_skill_manager().match_keywords(idea)


def skills_text(skills: list, agent_id: str) -> str:
    """拼出『target 命中当前 agent』的 skill 正文（注入 agent prompt）。"""
    manager = get_skill_manager()
    manager.activate(skills or [])
    return manager.get_skill_instructions(agent_id)


def needs_tools_for(skills: list, agent_id: str) -> Set[str]:
    """当前 agent 在命中 skill 中需要的工具（target 或 collaborator）。"""
    manager = get_skill_manager()
    tools = set()
    for sid in skills or []:
        skill = manager.get(sid)
        if not skill:
            continue
        if agent_id == skill.target_agent or agent_id in skill.collaborator_agents:
            tools.update(skill.required_tools or [])
    return tools
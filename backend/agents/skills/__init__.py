"""Skill 系统导出接口。

参考 daily_stock_analysis 的 skill 包结构：
- base: SkillManager, Skill
- router: SkillRouter
"""
from .base import (
    Skill,
    SkillManager,
    get_skill_manager,
    load_skill_from_yaml,
    load_skills_from_directory,
)
from .router import (
    SkillRouter,
    route_skills,
)

__all__ = [
    "Skill",
    "SkillManager",
    "get_skill_manager",
    "load_skill_from_yaml",
    "load_skills_from_directory",
    "SkillRouter",
    "route_skills",
]
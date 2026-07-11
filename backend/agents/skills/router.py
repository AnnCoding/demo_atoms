"""Skill 路由器：根据上下文智能选择 Skill。

参考 daily_stock_analysis 的 SkillRouter：
- 用户显式请求优先
- 关键词匹配
- 默认 fallback
"""
import logging
from typing import List, Optional
from .base import SkillManager, get_skill_manager

log = logging.getLogger("atoms.skills.router")


class SkillRouter:
    """Skill 路由器：智能选择适用的 Skill。"""

    def __init__(self, skill_manager: Optional[SkillManager] = None):
        self.manager = skill_manager or get_skill_manager()

    def select_skills(
        self,
        user_input: str,
        requested_skills: Optional[List[str]] = None,
        mode: str = "auto"
    ) -> List[str]:
        """选择适用的 Skill。

        优先级：
        1. 用户显式请求（requested_skills）
        2. 关键词匹配（user_input）
        3. 默认路由 skill（default_router=True）
        4. 空列表（无 skill）

        Args:
            user_input: 用户输入文本（idea）
            requested_skills: 用户显式请求的 skill 名称列表
            mode: 选择模式（"auto" / "manual"）

        Returns:
            选中的 skill 名称列表
        """
        # 1. 用户显式请求优先
        if requested_skills:
            valid = []
            for name in requested_skills:
                if self.manager.get(name):
                    valid.append(name)
                else:
                    log.warning(f"Requested skill not found: {name}")
            if valid:
                log.info(f"Skills selected by user request: {valid}")
                return valid

        # 2. 关键词匹配
        matched = self.manager.match_keywords(user_input)
        if matched:
            log.info(f"Skills matched by keywords: {matched}")
            return matched

        # 3. 默认路由 fallback（auto 模式）
        if mode == "auto":
            default_skills = self.manager.list_default_router_skills()
            if default_skills:
                names = [s.name for s in default_skills[:3]]  # 最多3个
                log.info(f"Skills selected by default router: {names}")
                return names

        # 4. 无 skill
        log.info("No skills selected")
        return []

    def get_skill_for_agent(self, agent_id: str, selected_skills: List[str]) -> List[str]:
        """获取指定 agent 相关的 skill（target 或 collaborator）。

        Args:
            agent_id: Agent ID
            selected_skills: 已选中的 skill 名称列表

        Returns:
            与该 agent 相关的 skill 名称列表
        """
        relevant = []
        for name in selected_skills:
            skill = self.manager.get(name)
            if not skill:
                continue
            if skill.target_agent == agent_id or agent_id in skill.collaborator_agents:
                relevant.append(name)
        return relevant


def route_skills(
    user_input: str,
    requested_skills: Optional[List[str]] = None,
    mode: str = "auto"
) -> List[str]:
    """便捷函数：路由选择 skill。

    Args:
        user_input: 用户输入文本
        requested_skills: 用户显式请求的 skill
        mode: 选择模式

    Returns:
        选中的 skill 名称列表
    """
    router = SkillRouter()
    return router.select_skills(user_input, requested_skills, mode)
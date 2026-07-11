"""元信息:智能体 / 模式 / 连接器 / skills(给前端渲染)。"""
from fastapi import APIRouter

from agents.registry import list_agents
from connectors.registry import list_connectors
from modes.registry import get_modes
from skills import loader as skills_loader

router = APIRouter()


@router.get("/agents")
def agents():
    return {"agents": list_agents()}


@router.get("/modes")
def modes():
    return {"modes": get_modes()}


@router.get("/connectors")
def connectors():
    return {"connectors": list_connectors()}


@router.get("/skills")
def skills():
    return {"skills": skills_loader.catalog()}

"""Persistent user-skill registry and configurable install pipeline.

User skills are declarative prompt modules only. They may request tools already
registered by the host, but cannot install Python/JS code or introduce arbitrary
executables. Built-in strategies are read-only and can never be overwritten.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import time
from typing import Any

import yaml

from agents.registry import AGENTS
from agents.skills.base import SkillManager, load_skill_from_yaml
from tools.registry import TOOLS


DATA_DIR = Path(__file__).parent.parent.parent / "data"
USER_SKILLS_DIR = Path(os.getenv("USER_SKILLS_DIR", DATA_DIR / "user_skills"))
REGISTRY_PATH = USER_SKILLS_DIR / "_registry.json"
USER_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
MAX_SKILL_BYTES = 64 * 1024
MAX_INSTRUCTIONS = 30_000


def _read_registry() -> dict[str, dict]:
    try:
        with open(REGISTRY_PATH, encoding="utf-8") as file:
            value = json.load(file)
            return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_registry(registry: dict[str, dict]) -> None:
    tmp = REGISTRY_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as file:
        json.dump(registry, file, ensure_ascii=False, indent=2)
    os.replace(tmp, REGISTRY_PATH)


def _builtin_names() -> set[str]:
    manager = SkillManager()
    manager.load_builtin_skills()
    return {skill.name for skill in manager.list_all_skills()}


def _validate_document(data: Any) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Skill 文件必须是 YAML/JSON 对象")
    name = str(data.get("name") or "").strip()
    if not NAME_RE.fullmatch(name):
        raise ValueError("name 必须为 3-64 位小写字母、数字、- 或 _，且以字母开头")
    if name in _builtin_names():
        raise ValueError("不能覆盖系统内置 Skill")
    target = str(data.get("target_agent") or "alex")
    if target not in AGENTS:
        raise ValueError(f"未知 target_agent: {target}")
    collaborators = data.get("collaborator_agents") or []
    if isinstance(collaborators, str):
        collaborators = [collaborators]
    unknown_agents = [agent for agent in collaborators if agent not in AGENTS]
    if unknown_agents:
        raise ValueError(f"未知 collaborator_agents: {unknown_agents}")
    tools = data.get("required_tools") or []
    if isinstance(tools, str):
        tools = [tools]
    unknown_tools = [tool for tool in tools if tool not in TOOLS]
    if unknown_tools:
        raise ValueError(f"Skill 只能使用系统已注册工具，未知工具: {unknown_tools}")
    instructions = str(data.get("instructions") or "").strip()
    if len(instructions) < 20:
        raise ValueError("instructions 至少需要 20 个字符")
    if len(instructions) > MAX_INSTRUCTIONS:
        raise ValueError(f"instructions 不能超过 {MAX_INSTRUCTIONS} 字符")
    data = dict(data)
    data["name"] = name
    data["target_agent"] = target
    data["collaborator_agents"] = collaborators
    data["required_tools"] = tools
    data["instructions"] = instructions
    return data


class SkillInstallPipeline:
    """validate -> normalize -> persist -> activate; each stage is observable."""

    def install(self, content: bytes, filename: str, owner_id: str = "local-user") -> dict:
        if not content or len(content) > MAX_SKILL_BYTES:
            raise ValueError(f"Skill 文件大小必须在 1-{MAX_SKILL_BYTES} bytes")
        stages: list[dict] = []
        try:
            raw = yaml.safe_load(content.decode("utf-8"))
            stages.append({"name": "parse", "status": "completed"})
            data = _validate_document(raw)
            stages.append({"name": "validate", "status": "completed"})
            name = data["name"]
            path = USER_SKILLS_DIR / f"{name}.yaml"
            with open(path, "w", encoding="utf-8") as file:
                yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)
            stages.append({"name": "persist", "status": "completed"})
            # Re-load canonical file through the same runtime parser.
            skill = load_skill_from_yaml(path)
            registry = _read_registry()
            now = int(time.time())
            previous = registry.get(name, {})
            registry[name] = {
                "name": name,
                "owner_id": owner_id or "local-user",
                "filename": filename,
                "enabled": True,
                "created_at": previous.get("created_at", now),
                "updated_at": now,
            }
            _write_registry(registry)
            stages.append({"name": "activate", "status": "completed"})
            return {"skill": {**skill.to_dict(), **registry[name], "source": "user"}, "pipeline": stages}
        except Exception as exc:
            stages.append({"name": "failed", "status": "failed", "message": str(exc)})
            setattr(exc, "pipeline", stages)
            raise


def list_user_skills(owner_id: str | None = None) -> list[dict]:
    registry = _read_registry()
    items = []
    for name, meta in registry.items():
        if owner_id and meta.get("owner_id") != owner_id:
            continue
        path = USER_SKILLS_DIR / f"{name}.yaml"
        if not path.exists():
            continue
        try:
            skill = load_skill_from_yaml(path)
            items.append({**skill.to_dict(), **meta, "source": "user"})
        except Exception as exc:
            items.append({**meta, "name": name, "source": "user", "invalid": True, "error": str(exc)})
    return sorted(items, key=lambda item: item.get("updated_at", 0), reverse=True)


def set_enabled(name: str, enabled: bool, owner_id: str = "local-user") -> dict:
    registry = _read_registry()
    record = registry.get(name)
    if not record or record.get("owner_id") != owner_id:
        raise KeyError("User Skill not found")
    record["enabled"] = bool(enabled)
    record["updated_at"] = int(time.time())
    _write_registry(registry)
    return record


def uninstall(name: str, owner_id: str = "local-user") -> None:
    registry = _read_registry()
    record = registry.get(name)
    if not record or record.get("owner_id") != owner_id:
        raise KeyError("User Skill not found")
    path = USER_SKILLS_DIR / f"{name}.yaml"
    if path.exists():
        path.unlink()
    registry.pop(name, None)
    _write_registry(registry)


def template() -> str:
    return """name: my-custom-skill
display_name: 我的自定义 Skill
description: 描述这个 Skill 解决什么问题
category: custom
trigger_keywords: [关键词1, 关键词2]
target_agent: alex
collaborator_agents: []
required_tools: []
default_active: false
default_router: false
default_priority: 50
instructions: |
  在这里填写会注入 Agent Prompt 的详细工作步骤、约束与输出格式。
  请至少提供二十个字符，并明确说明成功标准。
"""

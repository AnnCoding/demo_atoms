"""Prompt 模板加载 + jinja2 渲染。改 YAML 不改代码。"""
import os

import yaml
from jinja2 import Template

PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def load_prompt(key: str) -> dict:
    with open(os.path.join(PROMPTS_DIR, f"{key}.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_prompt(key: str, ctx: dict) -> dict:
    p = load_prompt(key)
    user = Template(p.get("user_template", "{{ idea }}")).render(**ctx)
    return {
        "system": p["system"],
        "user": user,
        "tools": p.get("tools", []) or [],
    }

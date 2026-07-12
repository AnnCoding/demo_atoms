"""Fast, deterministic intent hints used before the LLM triage step.

This classifier deliberately does not replace Mike.  It supplies stable product
constraints (artifact type, task family and whether clarification is actually
needed) so prompt drift cannot silently route the same request differently.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re


@dataclass
class IntentResult:
    task: str = "build"
    output_format: str = "single_html"
    complexity_hint: str = "simple"
    required_agents: list[str] = field(default_factory=lambda: ["alex"])
    needs_research: bool = False
    confidence: float = 0.65
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def classify(text: str, mode: str = "team") -> IntentResult:
    value = (text or "").strip().lower()
    result = IntentResult()

    if re.search(r"调研|研究|竞品|市场|research|compare", value):
        result.task = "research"
        result.needs_research = True
        result.required_agents = ["iris"]
        result.reasons.append("包含调研或比较意图")
    if re.search(r"修改|调整|重构|优化|修复|改成|继续|refactor|fix", value):
        result.task = "modify"
        result.reasons.append("包含已有产物修改意图")

    format_rules = [
        ("markdown", r"markdown|\.md|文档|报告|方案|说明书"),
        ("multi_file", r"react|next\.js|vue|fastapi|后端|api|多文件|完整项目"),
        ("webpage", r"官网|landing|展示页|品牌页|作品集"),
        ("single_html", r"小工具|计算器|待办|记账|番茄钟|单页|html"),
    ]
    for fmt, pattern in format_rules:
        if re.search(pattern, value):
            result.output_format = fmt
            result.confidence = 0.88
            result.reasons.append(f"命中 {fmt} 产物规则")
            break

    complex_hits = len(re.findall(r"用户|权限|登录|数据库|支付|实时|多角色|后台|接口|部署", value))
    if result.output_format == "multi_file" or complex_hits >= 2:
        result.complexity_hint = "complex"
        result.required_agents = list(dict.fromkeys(result.required_agents + ["emma", "bob", "alex"]))
        result.reasons.append("存在多模块或服务端约束")
    elif re.search(r"新品|从零|商业化|产品定义", value):
        result.complexity_hint = "new_product"
        result.required_agents = ["emma", "iris", "bob", "alex"]

    if mode == "deep_research":
        result.task = "research"
        result.needs_research = True
        result.required_agents = ["iris", "alex"]
    elif mode == "engineer":
        result.required_agents = ["alex"]
    return result

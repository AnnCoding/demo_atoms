"""模式 = 一条 Step DAG。team 以 triage 起,Mike 动态分流后再路由。"""
from dataclasses import dataclass
from typing import List, Optional, Union


@dataclass
class Step:
    agent: str
    output: str
    input_from: Union[str, List[str]] = "user"
    gate: bool = False
    prompt_key: Optional[str] = None
    kind: str = "run"  # "run"(普通步) | "triage"(Mike 分流步)


PIPELINES = {
    # 工程师模式:只 Alex,一步出应用
    "engineer": [
        Step("alex", output="code", input_from="user"),
    ],
    # 团队模式:Mike 先分流(提问/评估/路由),后续步由 orchestrator 动态替换
    "team": [
        Step("mike", output="triage", kind="triage", prompt_key="mike_triage"),
    ],
    # 深度研究模式:Iris 出报告 → 一键转网站
    "deep_research": [
        Step("iris", output="report", input_from="user"),
        Step("alex", output="code", input_from="report", gate=True),
    ],
}


def team_steps_after_triage(complexity: str) -> list:
    """Mike 分流完成后,按复杂度返回后续执行步骤。"""
    review = Step("mike", output="review", prompt_key="mike_review")
    if complexity == "simple":
        # 简单工程实现:跳过 PM/架构,Alex 直接基于功能要点清单做,再验收
        return [Step("alex", output="code"), review]
    # complex / new_product:完整团队接力
    return [
        Step("emma", output="spec"),
        Step("bob", output="arch"),
        Step("alex", output="code"),
        review,
    ]


def get_modes() -> list:
    return [
        {"id": "engineer", "name": "工程师模式", "emoji": "⚙️",
         "agents": ["alex"], "desc": "只激活 Alex,快、省,适合简单站/原型"},
        {"id": "team", "name": "团队模式", "emoji": "👥",
         "agents": ["mike", "emma", "bob", "alex"],
         "desc": "Mike 主管对接你:先澄清需求、评估复杂度并路由(简单→直接实现;复杂/新品→PM→架构→工程),最后验收"},
        {"id": "deep_research", "name": "深度研究模式", "emoji": "🔬",
         "agents": ["iris", "alex"], "desc": "Iris 出报告(可联网),可一键转网站"},
    ]

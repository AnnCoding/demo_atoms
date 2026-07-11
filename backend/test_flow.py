"""测试 Agent 执行状态流转."""
import asyncio
import json
import logging
from modes.registry import PIPELINES, team_steps_after_triage, Step
from core.session import new_session
from agents.skills import get_skill_manager

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("test")


def test_mode_pipelines():
    """测试各模式的初始 pipeline."""
    print("\n=== 测试模式 Pipeline ===")

    # 1. 工程师模式
    print("\n1. 工程师模式 (engineer):")
    steps = PIPELINES["engineer"]
    for i, step in enumerate(steps):
        print(f"  Step {i}: {step.agent} → {step.output} (kind={step.kind})")

    # 2. 团队模式
    print("\n2. 团队模式 (team):")
    steps = PIPELINES["team"]
    for i, step in enumerate(steps):
        print(f"  Step {i}: {step.agent} → {step.output} (kind={step.kind})")

    # 3. 深度研究模式
    print("\n3. 深度研究模式 (deep_research):")
    steps = PIPELINES["deep_research"]
    for i, step in enumerate(steps):
        print(f"  Step {i}: {step.agent} → {step.output} (gate={step.gate})")


def test_team_routing():
    """测试团队模式的分流路由."""
    print("\n=== 测试团队模式分流路由 ===")

    complexities = ["simple", "complex", "new_product"]
    for complexity in complexities:
        print(f"\n复杂度: {complexity}")
        steps = team_steps_after_triage(complexity)
        for i, step in enumerate(steps):
            print(f"  Step {i}: {step.agent} → {step.output}")


def test_session_creation():
    """测试 Session 创建."""
    print("\n=== 测试 Session 创建 ===")

    modes = ["engineer", "team", "deep_research"]
    for mode in modes:
        session = new_session(mode, "测试想法", [])
        print(f"\n模式: {mode}")
        print(f"  Session ID: {session.id[:8]}")
        print(f"  初始步骤数: {len(session.steps)}")
        print(f"  步骤: {[s.agent + '→' + s.output for s in session.steps]}")


def test_skill_matching():
    """测试 Skill 匹配逻辑."""
    print("\n=== 测试 Skill 匹配 ===")

    manager = get_skill_manager()

    test_cases = [
        "我想做一个 React dashboard",
        "帮我写一个 FastAPI 后端 API",
        "生成一个小工具计算器",
        "设计一个数据库表结构",
        "画一个系统架构图",
    ]

    for idea in test_cases:
        matched = manager.match_keywords(idea)
        print(f"\n输入: {idea}")
        print(f"  匹配的 skill: {matched}")
        if matched:
            for skill_id in matched:
                skill = manager.get(skill_id)
                print(f"    - {skill.display_name} (target: {skill.target_agent})")


def test_step_attributes():
    """测试 Step 属性."""
    print("\n=== 测试 Step 属性 ===")

    # 测试不同类型的 Step
    steps = [
        Step("mike", output="triage", kind="triage", prompt_key="mike_triage"),
        Step("alex", output="code", input_from="user"),
        Step("alex", output="code", input_from="report", gate=True),
    ]

    for i, step in enumerate(steps):
        print(f"\nStep {i}:")
        print(f"  agent: {step.agent}")
        print(f"  output: {step.output}")
        print(f"  input_from: {step.input_from}")
        print(f"  gate: {step.gate}")
        print(f"  kind: {step.kind}")
        print(f"  prompt_key: {step.prompt_key}")


def test_flow_simulation():
    """模拟执行流程."""
    print("\n=== 模拟执行流程 ===")

    # 1. 工程师模式流程
    print("\n【工程师模式流程】")
    session = new_session("engineer", "做一个记账小工具", [])
    print(f"初始状态: idx={session.idx}, steps={len(session.steps)}")

    # 模拟执行
    while session.idx < len(session.steps):
        step = session.steps[session.idx]
        print(f"  执行 Step {session.idx}: {step.agent} → {step.output}")
        session.artifacts[step.output] = f"[{step.output} 内容]"
        session.idx += 1

    print(f"完成状态: idx={session.idx}, artifacts={list(session.artifacts.keys())}")

    # 2. 团队模式流程（简单）
    print("\n【团队模式流程 - 简单】")
    session = new_session("team", "做一个简单的待办清单", [])
    print(f"初始状态: idx={session.idx}, steps={len(session.steps)}")

    # 模拟 Mike triage
    step = session.steps[session.idx]
    print(f"  执行 Step {session.idx}: {step.agent} → {step.output} (triage)")
    session.artifacts["triage"] = json.dumps({
        "complexity": "simple",
        "plan": "简单待办清单",
        "skills": ["single-page-app"]
    })

    # 分流后替换 steps
    complexity = "simple"
    session.steps = team_steps_after_triage(complexity)
    session.idx = 0
    print(f"分流后: complexity={complexity}, steps={len(session.steps)}")

    # 继续执行
    while session.idx < len(session.steps):
        step = session.steps[session.idx]
        print(f"  执行 Step {session.idx}: {step.agent} → {step.output}")
        session.artifacts[step.output] = f"[{step.output} 内容]"
        session.idx += 1

    print(f"完成状态: idx={session.idx}, artifacts={list(session.artifacts.keys())}")


if __name__ == "__main__":
    test_mode_pipelines()
    test_team_routing()
    test_session_creation()
    test_skill_matching()
    test_step_attributes()
    test_flow_simulation()

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
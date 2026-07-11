"""通用 Orchestrator:跑 session.steps、注入 Context/Skill、ReAct、分流路由、审批门、自愈、项目记忆。

skill 机制:team 模式 Mike 在 triage 选;engineer/deep_research 模式用关键词匹配(或用户手选 skill_id)。
执行步按 target 过滤注入 skill 正文,按 needs_tools 开放工具。
"""
import json
import logging
import re
import time
from typing import AsyncGenerator

from langsmith import trace

log = logging.getLogger("atoms.orch")

from agents.registry import AGENTS
from context.models import Context
from context.store import ATTACHMENTS
from core import llm
from core.memory import ProjectMemory
from core.sse import sse
from skills import loader as skills_loader
from tools import file_tools
from tools.registry import TOOLS


def build_context(session, step) -> Context:
    ctx = Context(idea=session.idea, artifacts=dict(session.artifacts))
    src = step.input_from
    if src == "user" or (isinstance(src, list) and "user" in src):
        for aid in session.attachment_ids:
            a = ATTACHMENTS.get(aid)
            if a:
                ctx.attachments.append(a)
    return ctx


def _skills_for_alex(session) -> list:
    """前端页面生成(single_html/webpage)时,强制带上 frontend-design 设计规范。

    覆盖所有模式——engineer/deep_research 模式 output_format 恒为 single_html 也能命中,
    不依赖关键词命中或 Mike 是否选中。multi_file/markdown 形态不注入。
    """
    skills = list(session.skills or [])
    fmt = getattr(session, "output_format", "single_html")
    if fmt in ("single_html", "webpage") and "frontend-design" not in skills:
        skills.append("frontend-design")
    return skills


def resolve_inputs(step, ctx: Context, session, agent_id: str) -> dict:
    data = {
        "idea": ctx.idea,
        "attachments_text": ctx.attachments_text(),
        "clarify_answers": session.clarify_answers,
        "skills": session.skills or [],
        "output_format": getattr(session, "output_format", "single_html"),
        "_session_id": session.id,
    }
    data.update(ctx.artifacts)
    if getattr(step, "kind", "run") == "triage":
        # 给 Mike 的 skill 目录(供其挑选)
        lines = [f"- {s['id']}: {s['name']} — {s['description']}" for s in skills_loader.catalog()]
        data["skills_catalog"] = "\n".join(lines) or "(暂无 skill)"
    # 给当前 agent 看的、target 命中的 skill 正文
    # Alex 生成前端页面(single_html/webpage)时,强制注入 frontend-design 设计规范
    alex_skills = _skills_for_alex(session) if agent_id == "alex" else (session.skills or [])
    data["skills_text"] = skills_loader.skills_text(alex_skills, agent_id)
    return data


def _parse_json(text: str):
    if not text:
        return None
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _extract_spec_features(session, spec_output: str) -> None:
    """尝试从 Emma 的 spec 输出中解析 JSON 并提取 core_features 列表。

    成功时存入 session.artifacts["core_features"]，失败时记录 warning 并原文传递。
    """
    parsed = _parse_json(spec_output)
    if parsed and isinstance(parsed, dict):
        features = parsed.get("core_features") or parsed.get("features") or []
        if isinstance(features, list) and features:
            session.artifacts["core_features"] = features
            log.info(
                "从 spec 提取到 %d 个 core_features", len(features),
                extra={"session_id": session.id, "agent": "Emma", "step": "spec_extract"},
            )
        else:
            log.warning(
                "spec JSON 中未找到 core_features 列表",
                extra={"session_id": session.id, "agent": "Emma", "step": "spec_extract"},
            )
    else:
        log.warning(
            "spec 输出非合法 JSON，原文传递",
            extra={"session_id": session.id, "agent": "Emma", "step": "spec_extract"},
        )


def _extract_plan_features(session, plan_text: str) -> None:
    """从 Mike triage 的 plan 中提取结构化功能清单，供 simple 模式下 Alex 使用。

    尝试解析 plan 中的编号列表或 bullet 列表，存入 session.artifacts["core_features"]。
    """
    if not plan_text:
        return
    lines = plan_text.strip().split("\n")
    features = []
    for line in lines:
        line = line.strip()
        # 匹配 "1. xxx" / "1) xxx" / "- xxx" / "• xxx"
        m = re.match(r"^(?:\d+[.)]\s*|[-\u2022]\s*)(.*)", line)
        if m and m.group(1).strip():
            features.append(m.group(1).strip())
    if features:
        session.artifacts["core_features"] = features
        log.info(
            "从 plan 提取到 %d 个功能点(simple模式)", len(features),
            extra={"session_id": session.id, "agent": "Mike", "step": "plan_extract"},
        )


def _needs_fix(review_output: str) -> bool:
    """检测 review 输出中是否包含"需修复"类关键词。"""
    if not review_output:
        return False
    fix_keywords = ["需修复", "需要修改", "需要修复", "需修改", "fix", "must fix", "打回"]
    lower = review_output.lower()
    return any(kw.lower() in lower for kw in fix_keywords)


def _extract_fix_instruction(review_output: str) -> str:
    """从 review 输出中提取问题描述作为修复指令。"""
    sections = re.split(r"\n#{1,3}\s*", review_output)
    fix_parts = []
    for sec in sections:
        sec_lower = sec.lower()
        if any(kw in sec_lower for kw in ["问题", "修复", "fix", "bug", "缺陷", "阻断"]):
            fix_parts.append(sec.strip())
    if fix_parts:
        return "\n".join(fix_parts)[:1500]
    return review_output[:800]


def _normalize_questions(qs):
    """把 clarify questions 规范成字符串数组。

    LLM 有时返回对象数组 [{"question":"...", "options":[...]}],前端无法直接渲染
    (React 报错 Objects are not valid as a React child)。统一转成
    "问题(选项1 / 选项2)" 字符串。
    """
    out = []
    for q in qs or []:
        if isinstance(q, str):
            out.append(q)
        elif isinstance(q, dict):
            text = str(q.get("question") or q.get("q") or q.get("text") or "").strip()
            opts = q.get("options") or []
            if opts:
                text = f"{text}({' / '.join(str(o) for o in opts)})"
            if text:
                out.append(text)
        else:
            out.append(str(q))
    return out


def _conv(session, role: str, agent: str, text):
    """追加一条对话历史到 session.conversation(落库后供作品页展示)。"""
    if text:
        session.conversation.append(
            {"role": role, "agent": agent or "", "text": str(text)}
        )


async def run_with_tools(agent, ctx_data: dict, prompt_key: str, extra_tools=None) -> AsyncGenerator[dict, None]:
    """ReAct 循环。tools = prompt 声明 ∪ skill 需要的工具。

    使用 langsmith.trace 上下文管理器实现动态 name/metadata/tags，
    并记录耗时和输出摘要。
    """
    from prompts.loader import render_prompt

    session_id = ctx_data.get("_session_id", "")
    iteration = ctx_data.get("iteration", 0)
    start = time.time()

    log.info(
        f"开始执行 prompt_key={prompt_key}",
        extra={"session_id": session_id, "agent": agent.name, "step": prompt_key},
    )

    p = render_prompt(prompt_key, ctx_data)
    tools = list(dict.fromkeys(list(p["tools"]) + list(extra_tools or [])))
    tools_called: list[str] = []

    with trace(
        name=f"{agent.name}({agent.role})",
        run_type="chain",
        metadata={
            "agent_id": agent.id,
            "agent_name": agent.name,
            "prompt_key": prompt_key,
            "session_id": session_id,
            "iteration": iteration,
        },
        tags=[agent.id, prompt_key],
    ) as run:
        content = ""

        if not tools:
            async for t in llm.stream(p["system"], p["user"]):
                yield {"type": "delta", "agent": agent.name, "text": t}
                content += t
        else:
            messages = [
                {"role": "system", "content": p["system"]},
                {"role": "user", "content": p["user"]},
            ]
            for _ in range(12):  # 工具轮上限(file_write 多文件会多次调用)
                msg = await llm.complete(messages, tools)
                content = msg["content"]
                if not msg["tool_calls"]:
                    yield {"type": "delta", "agent": agent.name, "text": content}
                    break
                messages.append({"role": "assistant", "content": content})
                for tc in msg["tool_calls"]:
                    tools_called.append(tc["name"])
                    yield {"type": "tool_call", "agent": agent.name,
                           "tool": tc["name"], "args": tc["args"]}
                    if tc["name"] in TOOLS:
                        res = await TOOLS[tc["name"]].call(**tc["args"])
                    else:
                        res = f"[未知工具 {tc['name']}]"
                    yield {"type": "tool_result", "tool": tc["name"], "result": (res or "")[:800]}
                    messages.append({"role": "user", "content": f"[tool {tc['name']} 返回]\n{res}"})
            else:
                # 达到工具轮上限，输出最后的 content
                yield {"type": "delta", "agent": agent.name, "text": content}

        # 记录 trace 输出
        run.end(outputs={
            "content_length": len(content),
            "tools_called": tools_called,
            "tools_count": len(tools_called),
        })

    duration_ms = (time.time() - start) * 1000
    log.info(
        f"完成 输出{len(content)}字符 工具调用{len(tools_called)}次",
        extra={
            "session_id": session_id,
            "agent": agent.name,
            "step": prompt_key,
            "duration_ms": duration_ms,
        },
    )


def _build_summary(session) -> str:
    """根据 session.artifacts 拼一个"做了什么"总结。"""
    agent_outputs = [
        ("report", "Iris 输出了调研报告"),
        ("spec", "Emma 产出了需求规格"),
        ("arch", "Bob 设计了技术架构"),
        ("code", "Alex 完成了代码实现"),
        ("review", "Mike 做了最终验收"),
    ]
    parts = [desc for key, desc in agent_outputs if session.artifacts.get(key)]
    files = session.artifacts.get("files") or []
    if isinstance(files, list) and files:
        parts.append(f"生成 {len(files)} 个文件")
    if session.iteration > 0:
        parts.append(f"完成第 {session.iteration} 轮迭代修改")
    return "\n".join(f"• {p}" for p in parts) if parts else "完成"


def _build_change_summary(session) -> str:
    """提取最近 5 轮用户修改指令作为变更历史摘要，防止多轮迭代中遗忘已完成的修改。"""
    history = session.history or []
    # 从 history 中提取 role=user 的条目（即用户的修改指令）
    user_msgs = [h["content"] for h in history if h.get("role") == "user"]
    # 取最近 5 条
    recent = user_msgs[-5:] if len(user_msgs) > 5 else user_msgs
    if not recent:
        return ""
    lines = []
    for i, msg in enumerate(recent, 1):
        # 截断过长的指令，保留核心信息
        short = msg[:120] + "…" if len(msg) > 120 else msg
        lines.append(f"第{i}轮: {short}")
    return "\n".join(lines)


async def _run_iteration(session, save_fn, mem) -> AsyncGenerator[str, None]:
    """多轮迭代:基于已有 code + 用户修改指令,让 Alex 重新生成。复用 run_with_tools + 自愈。"""
    from core.session import save_session
    from core.validator import validate_html

    iter_start = time.time()
    agent = AGENTS["alex"]
    _conv(session, "user", "", session.last_user_msg)  # 记录用户的迭代修改指令
    yield sse({"type": "phase", "agent": agent.name, "emoji": agent.emoji,
               "role": f"第{session.iteration}轮迭代", "artifact": "code"})

    files = file_tools.list_workspace_files()
    ctx_data = {
        "idea": session.idea,
        "previous_code": session.artifacts.get("code", ""),
        "modify_instruction": session.last_user_msg,
        "iteration": session.iteration,
        "skills_text": skills_loader.skills_text(_skills_for_alex(session), "alex"),
        "existing_files": "\n".join(f["path"] for f in files) if files else "",
        "output_format": getattr(session, "output_format", "single_html"),
        "change_history": _build_change_summary(session),
        "_session_id": session.id,
    }
    out = ""
    async for evt in run_with_tools(agent, ctx_data, "alex"):
        yield sse(evt)
        if evt["type"] == "delta":
            out += evt["text"]

    session.artifacts["code"] = out
    mem.write_code(out)
    mem.append_progress(f"第{session.iteration}轮迭代完成")

    # 自愈:仅对「HTML 单文件」code 做 jsdom 校验
    if out and "<html" in out.lower():
        for attempt in range(2):
            verdict = await validate_html(out)
            log.info(f"  [{session.id[:8]}] 迭代校验 ok={verdict.get('ok')} attempt={attempt}")
            yield sse({"type": "validate", "ok": verdict.get("ok"),
                       "attempt": attempt, "skipped": verdict.get("skipped", False),
                       "errors": (verdict.get("errors") or [])[:5]})
            if verdict.get("ok") or verdict.get("skipped"):
                break
            yield sse({"type": "phase", "agent": agent.name,
                       "emoji": agent.emoji, "role": "修复中", "artifact": "code"})
            heal_ctx = dict(ctx_data)
            heal_ctx["fix_errors"] = "; ".join(verdict.get("errors") or [])[:1500]
            heal_ctx["previous_code"] = out[:8000]
            out = ""
            async for evt in run_with_tools(agent, heal_ctx, "alex"):
                yield sse(evt)
                if evt["type"] == "delta":
                    out += evt["text"]
            session.artifacts["code"] = out
            mem.write_code(out)

    # 记录对话历史,清空本次指令防止重复触发
    session.history.append({"role": "user", "content": session.last_user_msg})
    session.history.append({"role": "assistant",
                            "content": f"已按「{session.last_user_msg}」完成第{session.iteration}轮修改"})
    _conv(session, "assistant", "Alex",
          f"已按「{session.last_user_msg}」完成第 {session.iteration} 轮迭代修改")
    session.last_user_msg = ""

    proj = save_fn(session)
    mem.save_meta(proj)
    mem.append_progress("迭代落库完成")
    summary = _build_summary(session)
    iter_duration_ms = (time.time() - iter_start) * 1000
    log.info(
        f"迭代#{session.iteration}完成 projectId={proj.get('id')}",
        extra={
            "session_id": session.id,
            "agent": agent.name,
            "step": f"iteration#{session.iteration}",
            "duration_ms": iter_duration_ms,
        },
    )
    yield sse({"type": "done", "projectId": proj.get("id"),
               "shareUrl": f"/p/{proj.get('share_slug')}",
               "session_id": session.id,
               "skills": session.skills or [],
               "files": session.artifacts.get("files", []),
               "summary": summary,
               "iteration": session.iteration})


async def run(session, save_fn) -> AsyncGenerator[str, None]:
    from core.session import save_session
    from core.validator import validate_html
    from modes.registry import team_steps_after_triage

    run_start = time.time()
    mem = ProjectMemory(session.project_id)
    file_tools.set_workspace(session.project_id)

    # ---- 多轮迭代:用户发来修改指令,且初始 pipeline 已完成 → 只跑 Alex 迭代 ----
    if (session.last_user_msg and session.iteration > 0
            and session.artifacts.get("code")
            and session.idx >= len(session.steps)):
        async for evt in _run_iteration(session, save_fn, mem):
            yield evt
        return

    # 记录初始想法到对话历史(仅首次生成)
    if not session.conversation:
        _conv(session, "user", "", session.idea)

    # 非 team 模式:确定 skills(用户手选 > 关键词匹配)
    if session.mode != "team" and not session.skills:
        session.skills = skills_loader.match(session.idea)
        if session.skills:
            yield sse({"type": "routed", "complexity": session.mode,
                       "steps": [], "skills": session.skills})

    try:
        while session.idx < len(session.steps):
            step = session.steps[session.idx]
            agent = AGENTS[step.agent]

            # ---------- triage 步:Mike 分流 ----------
            if getattr(step, "kind", "run") == "triage":
                yield sse({"type": "phase", "agent": agent.name, "emoji": agent.emoji,
                           "role": "需求分流", "artifact": "triage"})
                ctx = build_context(session, step)
                ctx_data = resolve_inputs(step, ctx, session, agent.id)
                out = ""
                async for evt in run_with_tools(agent, ctx_data, step.prompt_key or agent.prompt_key):
                    yield sse(evt)
                    if evt["type"] == "delta":
                        out += evt["text"]
                tri = _parse_json(out) or {}
                session.artifacts["triage"] = out

                if tri.get("need_clarify") and session.clarify_round < 2:
                    session.clarify_round += 1
                    qs = _normalize_questions(tri.get("questions", []))
                    mem.add_decision(f"第{session.clarify_round}轮澄清: {qs}")
                    _conv(session, "assistant", "Mike",
                          "开工前先确认几个细节:\n" + "\n".join(f"· {q}" for q in qs))
                    yield sse({"type": "clarify", "questions": qs, "session_id": session.id})
                    return

                complexity = tri.get("complexity", "complex")
                plan = tri.get("plan", "")
                session.output_format = tri.get("output_format") or "single_html"
                session.artifacts["plan"] = plan

                # ---- simple 模式结构化 plan：提取功能清单供 Alex 使用 ----
                if complexity == "simple" and plan:
                    _extract_plan_features(session, plan)

                # Mike 选 skill + 关键词命中做并集
                # （Mike 漏选时也能补上 storage 等强相关 skill；Mike 没选则沿用原兜底）
                _mike_skills = tri.get("skills") or []
                if _mike_skills:
                    session.skills = list(dict.fromkeys(
                        _mike_skills + skills_loader.match_keywords(session.idea)))
                else:
                    session.skills = skills_loader.match(session.idea) or []
                session.steps = team_steps_after_triage(complexity)
                session.idx = 0
                log.info(
                    f"分流 complexity={complexity} skills={session.skills}",
                    extra={"session_id": session.id, "agent": "Mike", "step": "triage"},
                )
                mem.add_decision(f"分流 complexity={complexity} skills={session.skills}")
                mem.append_progress(f"路由 → {complexity},skills={session.skills}")
                _fmt_label = {"markdown": "Markdown文档", "single_html": "单页HTML",
                              "webpage": "精美网页", "multi_file": "多文件项目"}.get(
                    session.output_format, session.output_format)
                _conv(session, "assistant", "Mike",
                      f"需求分析({complexity}·产物:{_fmt_label}): {tri.get('summary', '')}\n执行计划: {plan}")
                yield sse({"type": "routed", "complexity": complexity,
                           "steps": [s.agent for s in session.steps],
                           "skills": session.skills,
                           "output_format": session.output_format,
                           "summary": tri.get("summary", ""),
                           "plan": plan})
                continue

            # ---------- 普通步 ----------
            log.info(
                f"{agent.name}({agent.role}) → {step.output}",
                extra={"session_id": session.id, "agent": agent.name, "step": step.output},
            )
            yield sse({"type": "phase", "agent": agent.name, "emoji": agent.emoji,
                       "role": agent.role, "artifact": step.output})
            ctx = build_context(session, step)
            ctx_data = resolve_inputs(step, ctx, session, agent.id)
            pkey = step.prompt_key or agent.prompt_key
            extra = skills_loader.needs_tools_for(session.skills or [], agent.id)

            out = ""
            async for evt in run_with_tools(agent, ctx_data, pkey, extra_tools=extra):
                yield sse(evt)
                if evt["type"] == "delta":
                    out += evt["text"]

            session.artifacts[step.output] = out

            # ---- 上游输出结构化提取：Emma spec → core_features ----
            if step.output == "spec":
                _extract_spec_features(session, out)

            _conv(session, "assistant", agent.name,
                  f"{step.output} 已完成" +
                  (f": {out[:120].strip()}…" if step.output in ("spec", "arch", "review", "report") else ""))
            session.idx += 1
            mem.append_progress(f"{agent.name} 产出 {step.output}")
            if step.output == "arch":
                mem.write_arch(out)
            if step.output == "code":
                mem.write_code(out)
                files = file_tools.list_workspace_files()
                if files:
                    session.artifacts["files"] = [f["path"] for f in files]
                    mem.append_progress(f"工作区文件: {[f['path'] for f in files]}")
                # 兜底：multi_file 模式下 out 可能不含完整 HTML，尝试读取 index.html 作为预览
                if "<html" not in (out or "").lower() and files:
                    index_content = file_tools.read_workspace_file("index.html")
                    if index_content and "<html" in index_content.lower():
                        session.artifacts["code"] = index_content
                        # 流式发送给前端以触发实时预览
                        yield sse({"type": "delta", "agent": "Alex", "text": index_content})
            if step.output == "review":
                mem.add_decision(f"验收结论: {out[:400]}")

                # ---- review → fix 循环：检测"需修复"并自动追加 Alex 修复 ----
                fix_round = 0
                while _needs_fix(out) and fix_round < 2:
                    fix_round += 1
                    fix_instruction = _extract_fix_instruction(out)
                    log.info(
                        "review 需修复，启动第 %d 轮自动修复", fix_round,
                        extra={"session_id": session.id, "agent": "Alex", "step": f"review_fix#{fix_round}"},
                    )
                    mem.append_progress(f"review 需修复，自动修复第{fix_round}轮")

                    # Alex 修复步
                    alex_agent = AGENTS["alex"]
                    yield sse({"type": "phase", "agent": alex_agent.name, "emoji": alex_agent.emoji,
                               "role": f"修复(第{fix_round}轮)", "artifact": "code"})
                    fix_ctx = dict(ctx_data)
                    fix_ctx["fix_instruction"] = fix_instruction
                    fix_ctx["previous_code"] = session.artifacts.get("code", "")[:8000]
                    fix_ctx["idea"] = session.idea
                    fix_ctx["skills_text"] = skills_loader.skills_text(_skills_for_alex(session), alex_agent.id)

                    fix_out = ""
                    async for evt in run_with_tools(alex_agent, fix_ctx, "alex", extra_tools=extra):
                        yield sse(evt)
                        if evt["type"] == "delta":
                            fix_out += evt["text"]

                    session.artifacts["code"] = fix_out
                    mem.write_code(fix_out)
                    _conv(session, "assistant", alex_agent.name,
                          f"已按验收反馈完成第{fix_round}轮修复")

                    # Mike 重新 review
                    yield sse({"type": "phase", "agent": agent.name, "emoji": agent.emoji,
                               "role": f"复审(第{fix_round}轮)", "artifact": "review"})
                    review_ctx = dict(ctx_data)
                    review_ctx["code"] = fix_out
                    out = ""
                    async for evt in run_with_tools(agent, review_ctx, "mike_review"):
                        yield sse(evt)
                        if evt["type"] == "delta":
                            out += evt["text"]

                    session.artifacts["review"] = out
                    mem.add_decision(f"复审第{fix_round}轮结论: {out[:400]}")
                    _conv(session, "assistant", agent.name,
                          f"复审第{fix_round}轮: {out[:120].strip()}…")

                if fix_round > 0:
                    log.info(
                        "review→fix 循环结束，共 %d 轮", fix_round,
                        extra={"session_id": session.id, "agent": "orchestrator", "step": "review_fix_done"},
                    )

            # 自愈:仅对「HTML 单文件」code 做 jsdom 校验
            code_to_validate = session.artifacts.get("code", out)
            if step.output == "code" and code_to_validate and "<html" in code_to_validate.lower():
                for attempt in range(2):
                    verdict = await validate_html(code_to_validate)
                    log.info(f"  [{session.id[:8]}] 校验 ok={verdict.get('ok')} attempt={attempt}")
                    yield sse({"type": "validate", "ok": verdict.get("ok"),
                               "attempt": attempt, "skipped": verdict.get("skipped", False),
                               "errors": (verdict.get("errors") or [])[:5]})
                    if verdict.get("ok") or verdict.get("skipped"):
                        break
                    yield sse({"type": "phase", "agent": agent.name,
                               "emoji": agent.emoji, "role": "修复中", "artifact": "code"})
                    heal_ctx = dict(ctx_data)
                    heal_ctx["fix_errors"] = "; ".join(verdict.get("errors") or [])[:1500]
                    heal_ctx["previous_code"] = code_to_validate[:8000]
                    code_to_validate = ""
                    async for evt in run_with_tools(agent, heal_ctx, pkey, extra_tools=extra):
                        yield sse(evt)
                        if evt["type"] == "delta":
                            code_to_validate += evt["text"]
                    session.artifacts["code"] = code_to_validate
                    out = code_to_validate
                    mem.write_code(code_to_validate)

            if step.gate:
                yield sse({"type": "approval", "artifact": step.output,
                           "value": out, "session_id": session.id})
                return

        proj = save_fn(session)
        mem.save_meta(proj)
        mem.append_progress("落库完成")
        run_duration_ms = (time.time() - run_start) * 1000
        log.info(
            f"完成 projectId={proj.get('id')} skills={session.skills} files={len(session.artifacts.get('files', []))}",
            extra={
                "session_id": session.id,
                "agent": "orchestrator",
                "step": "pipeline_done",
                "duration_ms": run_duration_ms,
            },
        )
        yield sse({"type": "done", "projectId": proj.get("id"),
                   "shareUrl": f"/p/{proj.get('share_slug')}",
                   "session_id": session.id,
                   "skills": session.skills or [],
                   "files": session.artifacts.get("files", []),
                   "summary": _build_summary(session),
                   "iteration": session.iteration})
    except Exception as e:
        from core.llm import LLMFatalError
        # LLM 永久性错误(余额不足等):给用户清晰可读的提示,不再重试
        if isinstance(e, LLMFatalError):
            log.error(
                f"LLM 永久性错误 code={e.code}: {e}",
                extra={"session_id": session.id, "agent": "orchestrator", "step": "fatal_error"},
            )
            msg = f"⚠️ {e}"
            mem.append_progress(f"LLM 错误(停止): {e}")
            yield sse({"type": "error", "message": msg, "fatal": True})
            return
        run_duration_ms = (time.time() - run_start) * 1000
        log.error(
            f"出错: {type(e).__name__}: {e}",
            exc_info=True,
            extra={
                "session_id": session.id,
                "agent": "orchestrator",
                "step": "error",
                "duration_ms": run_duration_ms,
            },
        )
        mem.append_progress(f"出错: {type(e).__name__}: {e}")
        yield sse({"type": "error", "message": f"{type(e).__name__}: {e}"})
    finally:
        save_session(session)

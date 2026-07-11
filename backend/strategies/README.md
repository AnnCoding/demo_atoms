# Strategies 目录 - Skill 定义（YAML 格式）

本目录存放所有 Skill 的 YAML 定义文件。参考 `daily_stock_analysis` 项目的架构设计。

## 架构说明

### 核心原则

- **Skill 内嵌在 Agent 中**，而不是暴露在外部作为独立的 slash command
- **YAML 格式定义**，而不是 Markdown SKILL.md
- **通过 SkillManager 管理**，而不是简单的文件加载
- **Skill instructions 注入到 Agent 的 system prompt**，而不是独立的 skill prompt

### 目录结构

```
backend/
├── strategies/              # Skill 定义（YAML）
│   ├── react-app.yaml
│   ├── backend-api.yaml
│   ├── single-page-app.yaml
│   ├── arch-diagram.yaml
│   ├── database-design.yaml
│   ├── deploy-docker.yaml
│   ├── test-suite.yaml
│   └── README.md
│
├── agents/
│   ├── skills/             # Skill 管理模块（内嵌）
│   │   ├── base.py        # SkillManager + Skill 类
│   │   ├── router.py      # SkillRouter（智能路由）
│   │   └── __init__.py    # 导出接口
│   └ registry.py          # Agent 注册表
│
├── skills/
│   └ loader.py            # 兼容接口（使用 SkillManager）
│
└── core/
    └ orchestrator.py      # 使用 SkillManager 注入 skill instructions
```

## Skill YAML 格式

```yaml
name: react-app # Skill 唯一标识
display_name: React / Next.js 前端应用 # 显示名称
description: 生成多文件 Next.js 项目 # 描述（用于前端展示）
category: frontend # 分类（frontend/backend/design/testing/deployment）
trigger_keywords: # 触发关键词
  - react
  - next.js
  - dashboard
target_agent: alex # 主要负责的 Agent
collaborator_agents: [] # 协作 Agent 列表
required_tools: # 需要的工具
  - file_write
  - file_read
default_active: false # 是否默认激活
default_router: true # 是否参与自动路由
default_priority: 10 # 优先级（数字越小优先级越高）

instructions: | # 详细指导（注入到 Agent prompt）
  生成一个可直接 `npm install && npm run dev` 跑起来的 Next.js 14 项目...

  1. 配置文件...
  2. 入口文件...
  3. 组件...
```

## 核心组件

### 1. SkillManager (`agents/skills/base.py`)

负责：

- 加载 YAML 定义文件
- 注册和管理 Skill
- 激活/禁用 Skill
- 生成 Skill instructions（注入到 Agent）
- 关键词匹配

```python
from agents.skills import get_skill_manager

manager = get_skill_manager()
manager.load_builtin_skills()       # 加载 strategies/*.yaml
manager.activate(['react-app'])     # 激活指定 skill
instructions = manager.get_skill_instructions('alex')  # 生成 instructions
```

### 2. SkillRouter (`agents/skills/router.py`)

负责：

- 智能选择 Skill
- 用户显式请求优先
- 关键词匹配
- 默认 fallback

```python
from agents.skills import route_skills

matched = route_skills('我想做一个 React dashboard')
# 返回: ['react-app']
```

### 3. Skill 注入到 Agent

在 `core/orchestrator.py` 中：

```python
# 1. 路由选择 Skill
session.skills = route_skills(session.idea)

# 2. 激活 Skill
manager = get_skill_manager()
manager.activate(session.skills)

# 3. 生成 instructions 并注入到 Agent prompt
instructions = manager.get_skill_instructions(agent_id)
# instructions 会通过 skills_loader.skills_text() 注入到 agent 的 system prompt
```

## 使用方式

### 方式一：自动路由（推荐）

用户输入 idea，系统自动匹配 Skill：

```python
from agents.skills import route_skills

matched = route_skills('帮我做一个 React dashboard')
# 自动匹配: ['react-app']
```

### 方式二：用户显式指定

用户在请求中指定 Skill：

```python
session.skills = ['react-app', 'backend-api']
```

### 方式三：默认激活

设置 `default_active: true` 的 Skill 会自动激活。

## 扩展 Skill

1. 在 `strategies/` 目录下创建新的 YAML 文件
2. 填写必要的字段（name, display_name, instructions 等）
3. 无需修改代码，系统自动加载

## 与 daily_stock_analysis 的对比

| 项目           | daily_stock_analysis       | demo_show（重构后）        |
| -------------- | -------------------------- | -------------------------- |
| Skill 定义格式 | YAML（strategies/*.yaml）  | YAML（strategies/*.yaml）  |
| Skill 管理模块 | src/agent/skills/          | agents/skills/             |
| SkillManager   | base.py                    | base.py                    |
| SkillRouter    | router.py                  | router.py                  |
| 注入方式       | 注入到 Agent system prompt | 注入到 Agent system prompt |
| 是否暴露在外部 | ❌ 内嵌在 Agent            | ❌ 内嵌在 Agent            |

## 优势

✅ **内嵌架构**：Skill 作为 Agent 的内部能力模块，不暴露给用户
✅ **YAML 格式**：比 Markdown 更结构化，易于解析和管理
✅ **智能路由**：关键词匹配 + 默认 fallback，自动选择适用的 Skill
✅ **性能优化**：模块级缓存（prototype + deepcopy），避免重复读磁盘
✅ **易于扩展**：新增 Skill 只需添加 YAML 文件，无需改代码

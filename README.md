# Atoms-Demo

智能体驱动生成应用的可运行 Demo(笔试项目)。参考 [Atoms](https://atoms.dev/)。

## 架构（v2 Agent Runtime）

- **前端** `frontend/` — Next.js 14 + Tailwind,三栏工作台、模式切换、附件上传、iframe 预览
- **后端** `backend/` — Python FastAPI,五支柱编排
  - `prompts/` 可迭代 Prompt 模板(YAML + jinja2)
  - `agents/` 7 智能体注册表(Mike/Emma/Bob/Alex/David/Iris/Sarah)
  - `modes/` 3 模式流水线(工程师 / 团队 / 深度研究)
  - `context/` 附件摄取(统一多模态 Context)
  - `connectors/` MCP 兼容连接器(web_search)
  - `core/` 通用 Orchestrator(模式无关)+ llm/db/sse/session

v2 新增能力：

- 双层意图识别（确定性规则 + Mike 语义分流）
- 版本化结构事件协议与可点击澄清选项
- DAG 并行 Agent wave（Emma 与 Iris 并发）
- Session、作品对话、`memory.json` 分层记忆
- 工具超时、重复调用熔断、节点 checkpoint、可选分支降级
- LangSmith Agent/Tool 嵌套 trace，记录 Prompt、参数、结果、状态与耗时
- 用户 Skill 安装链路（解析、校验、持久化、启停、运行时热合并）
- 私有知识库、长期知识记忆、任务知识选择与可控发布的知识广场

设计细节见 [ARCHITECTURE_V2.md](./ARCHITECTURE_V2.md)。

## 快速开始

### 后端

```bash
cd backend
cp .env.example .env          # 填 LLM / Supabase(可不填,用本地 stub)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# 访问 http://localhost:8000/health
```

### 前端

```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_BASE=http://localhost:8000
npm install
npm run dev
# 访问 http://localhost:3000
```

## 设计文档

完整运行架构见 `ARCHITECTURE_V2.md`；原始题目与方案仍保留在飞书文档。

## 验证

```bash
PYTHONPATH=backend python3 -m unittest backend/test_architecture_v2.py
PYTHONPATH=backend python3 -m unittest backend/test_extensibility.py
python3 backend/test_flow.py
cd frontend && npm run build
```

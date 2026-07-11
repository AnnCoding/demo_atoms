# Atoms-Demo

智能体驱动生成应用的可运行 Demo(笔试项目)。参考 [Atoms](https://atoms.dev/)。

## 架构(五支柱)

- **前端** `frontend/` — Next.js 14 + Tailwind,三栏工作台、模式切换、附件上传、iframe 预览
- **后端** `backend/` — Python FastAPI,五支柱编排
  - `prompts/` 可迭代 Prompt 模板(YAML + jinja2)
  - `agents/` 7 智能体注册表(Mike/Emma/Bob/Alex/David/Iris/Sarah)
  - `modes/` 3 模式流水线(工程师 / 团队 / 深度研究)
  - `context/` 附件摄取(统一多模态 Context)
  - `connectors/` MCP 兼容连接器(web_search)
  - `core/` 通用 Orchestrator(模式无关)+ llm/db/sse/session

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

完整方案见飞书文档(五支柱整合版)。

"""Atoms-Demo API 入口。"""
import logging
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import approve, chat, generate, knowledge, meta, projects, skills, upload
from core.log import setup

load_dotenv()
setup()
log = logging.getLogger("atoms.main")

app = FastAPI(title="Atoms Demo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(approve.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")


@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    dur = (time.time() - start) * 1000
    log.info(f"{request.method} {request.url.path} -> {response.status_code} ({dur:.0f}ms)")
    return response


@app.on_event("startup")
async def startup():
    log.info("=" * 52)
    log.info("Atoms Demo API 启动")
    log.info(f"  LLM    : {os.getenv('LLM_MODEL')} @ {os.getenv('LLM_BASE_URL')}")
    log.info(f"  真DB   : {'on (DATABASE_URL)' if os.getenv('DATABASE_URL') else 'off (本地 JSON stub)'}")
    log.info(f"  短期记忆: {'Redis (REDIS_URL)' if os.getenv('REDIS_URL') else '内存'}")
    log.info(f"  CORS   : {os.getenv('CORS_ORIGINS', 'http://localhost:3000')}")
    log.info("=" * 52)


@app.get("/health")
def health():
    return {"ok": True, "service": "atoms-demo-api"}

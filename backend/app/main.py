from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router, service


@asynccontextmanager
async def lifespan(app: FastAPI):
    service.runtime.require_open()
    try:
        yield
    finally:
        service.close()


app = FastAPI(
    lifespan=lifespan,
    title="OpsQuery Studio API",
    version="1.0.0",
    description="OpsQuery Studio 智能数据分析平台：面向短视频运营场景的自然语言问数与结果分析服务。",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

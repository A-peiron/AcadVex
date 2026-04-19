from fastapi import FastAPI
from api.routes.chat import router as chat_router
from contextlib import asynccontextmanager
from agent.loop import _langfuse

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    _langfuse.flush()

# 创建 FastAPI 应用实例
# title/description/version 会显示在 /docs 的 Swagger UI 页面顶部
app = FastAPI(
    title="AcadVex API",
    description="学术合作网络智能分析平台，基于 FPGCL 模型 + DeepSeek LLM",
    version="0.1.0",
    lifespan=lifespan,
)

# 挂载路由：chat_router 里所有路由都加上 /api 前缀
# 例如 chat_router 里的 /chat → 实际访问路径 /api/chat
app.include_router(chat_router, prefix="/api")

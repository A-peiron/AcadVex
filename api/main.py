from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from api.routes.chat import router as chat_router
from api.routes.authors import router as authors_router
from api.routes.graph import router as graph_router
from api.routes.recommendations import router as recommendations_router
from api.middleware.security import SecurityMiddleware
from contextlib import asynccontextmanager
from agent.loop import _langfuse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from api.middleware.rate_limit import limiter
from agent.utils.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    _langfuse.flush()

app = FastAPI(
    title="AcadVex API",
    description="学术合作网络智能分析平台，基于 FPGCL 模型 + DeepSeek LLM",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("api_error", path=str(request.url.path), error=str(exc))
    return JSONResponse(status_code=500, content={"error": "服务器内部错误"})

@app.get("/health")
async def health_check():
    from pathlib import Path
    checks = {
        "data_files": "ok" if Path("data/graph_stats/dblp/author_meta.json").exists() else "missing",
        "centrality": "ok" if Path("data/precomputed/centrality.json").exists() else "missing",
    }
    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, **checks}

# 挂载路由：chat_router 里所有路由都加上 /api 前缀
# 例如 chat_router 里的 /chat → 实际访问路径 /api/chat
app.include_router(chat_router, prefix="/api")
app.include_router(authors_router, prefix="/api")
app.include_router(graph_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")

# 安全中间件（必须在路由注册之后添加）
app.add_middleware(SecurityMiddleware)

import re
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# ── 注入攻击关键词黑名单（正则，大小写不敏感） ──────────────────────────────
INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+instructions?",
    r"forget\s+(everything|all|your)\s*(you|previous)?",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(a\s+)?(?:different|new|another|evil|unrestricted)",
    r"jailbreak",
    r"prompt\s+injection",
    r"忽略.{0,10}(指令|提示|规则|约束)",  # 更宽松：忽略 + 0-10个任意字符 + 关键词
    r"你现在是",
    r"扮演.{0,10}(助手|机器人|AI|模型)",
    r"不受(限制|约束|规则)",
    r"(system\s*prompt|系统提示词).{0,20}(泄露|输出|告诉我|reveal|leak|show)",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

# 请求体最大长度（字符数）
MAX_BODY_LENGTH = 2000

# 只检查需要读 body 的路径（POST 且有 message 字段的端点）
PROTECTED_PATHS = {"/api/chat"}


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    安全中间件：在请求到达路由处理器之前拦截恶意输入。

    检测内容：
    1. 请求体过大（超过 MAX_BODY_LENGTH 字符）→ 413
    2. 包含 prompt 注入关键词 → 400
    """

    async def dispatch(self, request: Request, call_next):
        # 只检查受保护的 POST 路径
        if request.method == "POST" and request.url.path in PROTECTED_PATHS:
            # ── 读取请求体 ──────────────────────────────────────────────────
            raw_body = await request.body()

            # 检查 1：请求体大小
            if len(raw_body) > MAX_BODY_LENGTH:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"请求体过长（最大 {MAX_BODY_LENGTH} 字符）"
                    },
                )

            # 检查 2：提取 message 字段，扫描注入关键词
            try:
                body_json = json.loads(raw_body)
                message = body_json.get("message", "")
            except (json.JSONDecodeError, AttributeError):
                message = raw_body.decode("utf-8", errors="ignore")

            for pattern in _COMPILED_PATTERNS:
                if pattern.search(message):
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "输入包含不允许的内容"},
                    )

            # ── 把 body 放回去（Starlette 只能读一次，需要重新注入） ──────────
            async def receive():
                return {"type": "http.request", "body": raw_body}

            request = Request(request.scope, receive)

        return await call_next(request)

import asyncio
import json
from typing import Dict, List
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from api.schemas import ChatRequest, ChatResponse
from agent.loop import run_agent, run_agent_stream
from api.middleware.rate_limit import limiter

router = APIRouter()

# 会话历史存储（内存，生产环境应使用 Redis/数据库）
_session_history: Dict[str, List[dict]] = {}


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest) -> ChatResponse:
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(None, run_agent, req.message)
    return ChatResponse(answer=answer)


@router.post("/chat/stream")
@limiter.limit("20/minute")
def chat_stream(request: Request, req: ChatRequest) -> StreamingResponse:
    session_id = req.session_id or "default"

    # 获取历史消息
    history = _session_history.get(session_id, [])

    def event_generator():
        assistant_response = ""
        for event in run_agent_stream(req.message, history):
            if event["type"] == "token":
                assistant_response += event["content"]
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        # 保存本轮对话到历史
        if session_id not in _session_history:
            _session_history[session_id] = []
        _session_history[session_id].append({"role": "user", "content": req.message})
        _session_history[session_id].append({"role": "assistant", "content": assistant_response})

        # 限制历史长度（最多保留最近 20 轮对话）
        if len(_session_history[session_id]) > 40:
            _session_history[session_id] = _session_history[session_id][-40:]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
